"""agent-system-updater — upstream diff/update tool.

Reads .agent-system-manifest.yaml (written by install.sh) and compares it
against the currently-installed files and the latest upstream sources.

Subcommands:
    check-updates           Summarize which files changed upstream.
    diff PATH               Show a unified diff of PATH vs its upstream copy.
    update [--apply]        Apply upstream changes. Without --apply runs as a
                            dry-run; with --apply backs up modified-by-user
                            files as .bak.<ts> before overwriting.

Intentionally stdlib-only (pyyaml is not installed by default in target
projects; we parse the fixed manifest schema ourselves, matching the
convention install.sh uses for plugins.yaml).

Exit codes:
    0  success (even when updates are available — that's the normal case)
    1  runtime failure (network, missing upstream, corrupt manifest)
    2  usage / bad argument
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path


MANIFEST_FILENAME = ".agent-system-manifest.yaml"


@dataclass
class FileRecord:
    path: str
    origin: str
    sha256: str


@dataclass
class PluginEntry:
    name: str
    source: str
    sha: str


@dataclass
class Manifest:
    version: int
    template_source: str
    template_sha: str
    plugins: list[PluginEntry] = field(default_factory=list)
    files: list[FileRecord] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Manifest parsing (schema-specific, not a general YAML parser)
# ---------------------------------------------------------------------------


def _strip_quotes(v: str) -> str:
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    return v


def parse_manifest(path: Path) -> Manifest:
    if not path.exists():
        raise SystemExit(f"manifest not found: {path}\n"
                         f"Run install.sh once to create it.")
    text = path.read_text(encoding="utf-8")

    version = 1
    template_source = ""
    template_sha = ""
    plugins: list[PluginEntry] = []
    files: list[FileRecord] = []

    state = None  # "template" | "plugins" | "files"
    current_plugin: dict | None = None
    current_file: dict | None = None

    for raw in text.splitlines():
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue

        # Top-level keys at column 0
        m = re.match(r"^([a-z_]+):\s*(.*)$", line)
        if m and not line.startswith(" "):
            key, val = m.group(1), m.group(2).strip()
            if current_plugin is not None:
                plugins.append(PluginEntry(
                    name=current_plugin.get("name", ""),
                    source=current_plugin.get("source", ""),
                    sha=current_plugin.get("sha", ""),
                ))
                current_plugin = None
            if current_file is not None:
                files.append(FileRecord(
                    path=current_file.get("path", ""),
                    origin=current_file.get("origin", ""),
                    sha256=current_file.get("sha256", ""),
                ))
                current_file = None
            if key == "manifest_version":
                version = int(_strip_quotes(val))
            elif key == "template":
                state = "template"
            elif key == "plugins":
                state = "plugins"
                if val == "[]":
                    state = "plugins-empty"
            elif key == "files":
                state = "files"
                if val == "[]":
                    state = "files-empty"
            else:
                state = None
            continue

        # Indented content
        stripped = line.strip()

        if state == "template":
            mm = re.match(r"([a-z_]+):\s*(.*)$", stripped)
            if mm:
                k, v = mm.group(1), mm.group(2).strip()
                if k == "source":
                    template_source = _strip_quotes(v)
                elif k == "sha":
                    template_sha = _strip_quotes(v)
            continue

        if state == "plugins":
            if stripped.startswith("- name:"):
                if current_plugin is not None:
                    plugins.append(PluginEntry(
                        name=current_plugin.get("name", ""),
                        source=current_plugin.get("source", ""),
                        sha=current_plugin.get("sha", ""),
                    ))
                current_plugin = {}
                current_plugin["name"] = _strip_quotes(stripped.split(":", 1)[1])
            elif ":" in stripped and current_plugin is not None:
                k, v = stripped.split(":", 1)
                current_plugin[k.strip()] = _strip_quotes(v)
            continue

        if state == "files":
            if stripped.startswith("- path:"):
                if current_file is not None:
                    files.append(FileRecord(
                        path=current_file.get("path", ""),
                        origin=current_file.get("origin", ""),
                        sha256=current_file.get("sha256", ""),
                    ))
                current_file = {}
                current_file["path"] = _strip_quotes(stripped.split(":", 1)[1])
            elif ":" in stripped and current_file is not None:
                k, v = stripped.split(":", 1)
                current_file[k.strip()] = _strip_quotes(v)
            continue

    if current_plugin is not None:
        plugins.append(PluginEntry(
            name=current_plugin.get("name", ""),
            source=current_plugin.get("source", ""),
            sha=current_plugin.get("sha", ""),
        ))
    if current_file is not None:
        files.append(FileRecord(
            path=current_file.get("path", ""),
            origin=current_file.get("origin", ""),
            sha256=current_file.get("sha256", ""),
        ))

    return Manifest(
        version=version,
        template_source=template_source,
        template_sha=template_sha,
        plugins=plugins,
        files=files,
    )


# ---------------------------------------------------------------------------
# Upstream fetch — shallow-clone sources to a temp dir
# ---------------------------------------------------------------------------


@dataclass
class Upstream:
    template_dir: Path
    template_sha: str
    plugins_dir: Path | None
    plugins_sha: str
    plugin_subpaths: dict[str, str]   # plugin name -> relative dir inside plugins repo


def fetch_upstream(manifest: Manifest, tmp_root: Path) -> Upstream:
    """Clone template + plugins repos (shallow) so we can diff against them."""
    template_dir = tmp_root / "template-repo"
    _run(["git", "clone", "--depth=1", "--quiet", manifest.template_source, str(template_dir)])
    template_sha = _sha(template_dir)

    plugins_dir: Path | None = None
    plugins_sha = ""
    plugin_subpaths: dict[str, str] = {}
    # A repo may host several plugins; we clone once and reuse.
    if manifest.plugins:
        plugins_dir = tmp_root / "plugins-repo"
        _run(["git", "clone", "--depth=1", "--quiet",
              manifest.plugins[0].source, str(plugins_dir)])
        plugins_sha = _sha(plugins_dir)
        # Read plugins.yaml to find each plugin's subpath
        plugins_yaml = plugins_dir / "plugins.yaml"
        if plugins_yaml.exists():
            entries = _parse_plugins_yaml(plugins_yaml)
            for e in entries:
                plugin_subpaths[e["name"]] = e.get("path", f"{e['name']}/")

    return Upstream(
        template_dir=template_dir,
        template_sha=template_sha,
        plugins_dir=plugins_dir,
        plugins_sha=plugins_sha,
        plugin_subpaths=plugin_subpaths,
    )


def _sha(repo: Path) -> str:
    out = _run(["git", "-C", str(repo), "rev-parse", "--short=12", "HEAD"])
    return out.strip() or "unknown"


def _run(cmd: list[str]) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(cmd)}\n{r.stderr}")
    return r.stdout


def _parse_plugins_yaml(path: Path) -> list[dict]:
    """Minimal reader for our known plugins.yaml schema."""
    entries: list[dict] = []
    current: dict | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped == "plugins:":
            continue
        m = re.match(r"-\s+name:\s*(.+)$", stripped)
        if m:
            if current is not None:
                entries.append(current)
            current = {"name": _strip_quotes(m.group(1))}
            continue
        mm = re.match(r"([a-zA-Z_]+)\s*:\s*(.*)$", stripped)
        if mm and current is not None:
            k, v = mm.group(1), _strip_quotes(mm.group(2))
            if v:
                current[k] = v
    if current is not None:
        entries.append(current)
    return entries


# ---------------------------------------------------------------------------
# sha256 helpers
# ---------------------------------------------------------------------------


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Core comparison
# ---------------------------------------------------------------------------


@dataclass
class Diff:
    path: str
    origin: str
    local_status: str    # "untouched" | "user-modified" | "missing"
    upstream_status: str # "same" | "changed" | "removed" | "unknown"
    manifest_sha: str
    local_sha: str | None
    upstream_sha: str | None


def _upstream_path(record: FileRecord, up: Upstream) -> Path | None:
    """Resolve a manifest record to the corresponding file in the cloned upstream."""
    if record.origin == "template":
        return up.template_dir / record.path
    if record.origin.startswith("plugin:"):
        name = record.origin.split(":", 1)[1]
        if up.plugins_dir is None:
            return None
        subpath = up.plugin_subpaths.get(name, f"{name}/")
        plugin_root = up.plugins_dir / subpath.rstrip("/")
        # Map DEST layout back to plugin source layout:
        #   plugins/<name>/{docs|samples|README*.md}  <-  origin docs/samples/README...
        #   everything else                            <-  as-is relative
        rel = record.path
        prefix = f"plugins/{name}/"
        if rel.startswith(prefix):
            rel = rel[len(prefix):]
        return plugin_root / rel
    return None


def compare(manifest: Manifest, dest: Path, up: Upstream) -> list[Diff]:
    out: list[Diff] = []
    for rec in manifest.files:
        local_file = dest / rec.path
        local_sha = sha256_file(local_file)
        if local_sha is None:
            local_status = "missing"
        elif local_sha == rec.sha256:
            local_status = "untouched"
        else:
            local_status = "user-modified"

        upstream_file = _upstream_path(rec, up)
        if upstream_file is None:
            upstream_status = "unknown"
            upstream_sha = None
        elif not upstream_file.is_file():
            upstream_status = "removed"
            upstream_sha = None
        else:
            upstream_sha = sha256_file(upstream_file)
            upstream_status = "same" if upstream_sha == rec.sha256 else "changed"

        out.append(Diff(
            path=rec.path,
            origin=rec.origin,
            local_status=local_status,
            upstream_status=upstream_status,
            manifest_sha=rec.sha256,
            local_sha=local_sha,
            upstream_sha=upstream_sha,
        ))
    return out


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_check(args) -> int:
    dest = Path(args.project_root or os.getcwd()).resolve()
    manifest = parse_manifest(dest / MANIFEST_FILENAME)

    with tempfile.TemporaryDirectory(prefix="agsys-") as tmp:
        tmp_root = Path(tmp)
        try:
            up = fetch_upstream(manifest, tmp_root)
        except RuntimeError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        diffs = compare(manifest, dest, up)

    counts = {"untouched+same": 0, "untouched+changed": 0,
              "user-modified+same": 0, "user-modified+changed": 0,
              "missing": 0, "upstream-removed": 0}
    incoming: list[Diff] = []
    conflicts: list[Diff] = []
    gone: list[Diff] = []
    missing_local: list[Diff] = []

    for d in diffs:
        if d.local_status == "missing":
            counts["missing"] += 1
            missing_local.append(d)
            continue
        if d.upstream_status == "removed":
            counts["upstream-removed"] += 1
            gone.append(d)
            continue
        key = f"{d.local_status}+{d.upstream_status}"
        counts[key] = counts.get(key, 0) + 1
        if d.local_status == "untouched" and d.upstream_status == "changed":
            incoming.append(d)
        if d.local_status == "user-modified" and d.upstream_status == "changed":
            conflicts.append(d)

    print(f"Manifest version:     {manifest.version}")
    print(f"Template installed:   {manifest.template_sha}  ({manifest.template_source})")
    print(f"Template upstream:    {up.template_sha}")
    for p in manifest.plugins:
        print(f"Plugin {p.name:<20} installed: {p.sha}  upstream: {up.plugins_sha}  ({p.source})")
    print()
    print(f"Total tracked files:          {len(manifest.files)}")
    print(f"  untouched + unchanged:      {counts.get('untouched+same', 0)}")
    print(f"  untouched + upstream-moved: {counts.get('untouched+changed', 0)}  ← safe to update")
    print(f"  user-modified + unchanged:  {counts.get('user-modified+same', 0)}  ← your edits, no conflict")
    print(f"  user-modified + upstream-moved: {counts.get('user-modified+changed', 0)}  ← 3-way needed")
    print(f"  locally missing:            {counts.get('missing', 0)}")
    print(f"  removed upstream:           {counts.get('upstream-removed', 0)}")

    if incoming:
        print()
        print(f"Safe updates available ({len(incoming)}):")
        for d in sorted(incoming, key=lambda x: x.path):
            print(f"  - {d.path}  [{d.origin}]")

    if conflicts:
        print()
        print(f"⚠ Conflicts ({len(conflicts)}) — both you and upstream changed the same file:")
        for d in sorted(conflicts, key=lambda x: x.path):
            print(f"  - {d.path}  [{d.origin}]")

    if missing_local:
        print()
        print(f"Missing locally ({len(missing_local)}):")
        for d in sorted(missing_local, key=lambda x: x.path)[:20]:
            print(f"  - {d.path}  [{d.origin}]")
        if len(missing_local) > 20:
            print(f"  ... and {len(missing_local) - 20} more")

    print()
    if incoming or conflicts:
        print("Next: `python bot/agent_system_updater.py diff <path>` to inspect, "
              "or `python bot/agent_system_updater.py update --apply` to adopt safe changes.")
    else:
        print("No updates available. Everything matches upstream.")

    return 0


def cmd_diff(args) -> int:
    dest = Path(args.project_root or os.getcwd()).resolve()
    manifest = parse_manifest(dest / MANIFEST_FILENAME)
    target_path = args.path

    rec = next((r for r in manifest.files if r.path == target_path), None)
    if rec is None:
        print(f"error: no manifest record for path: {target_path}", file=sys.stderr)
        return 2

    with tempfile.TemporaryDirectory(prefix="agsys-") as tmp:
        tmp_root = Path(tmp)
        try:
            up = fetch_upstream(manifest, tmp_root)
        except RuntimeError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1

        upstream_file = _upstream_path(rec, up)
        local_file = dest / rec.path

        if upstream_file is None or not upstream_file.is_file():
            print(f"# upstream copy of {rec.path} is missing "
                  f"(removed in a newer release, or plugin not re-mapped)", file=sys.stderr)
            return 1
        if not local_file.is_file():
            print(f"# local copy of {rec.path} is missing", file=sys.stderr)
            return 1

        local_lines = local_file.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
        upstream_lines = upstream_file.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)

        # difflib hunk headers (---, +++, @@) come without trailing newlines;
        # we want each diff line terminated, so use lineterm="\n" and rely on
        # the fact that local_lines/upstream_lines were read with keepends=True.
        diff = difflib.unified_diff(
            local_lines, upstream_lines,
            fromfile=f"local/{rec.path}",
            tofile=f"upstream/{rec.path}",
            lineterm="\n",
        )
        sys.stdout.writelines(diff)
        # Ensure trailing newline in case the last file line lacked one.
        sys.stdout.write("\n")
    return 0


def cmd_update(args) -> int:
    dest = Path(args.project_root or os.getcwd()).resolve()
    manifest_path = dest / MANIFEST_FILENAME
    manifest = parse_manifest(manifest_path)

    with tempfile.TemporaryDirectory(prefix="agsys-") as tmp:
        tmp_root = Path(tmp)
        try:
            up = fetch_upstream(manifest, tmp_root)
        except RuntimeError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1

        diffs = compare(manifest, dest, up)

        safe: list[Diff] = []
        conflicts: list[Diff] = []
        for d in diffs:
            if d.local_status == "missing":
                continue
            if d.upstream_status == "removed":
                continue
            if d.local_status == "untouched" and d.upstream_status == "changed":
                safe.append(d)
            elif d.local_status == "user-modified" and d.upstream_status == "changed":
                conflicts.append(d)

        if not safe and not conflicts:
            print("No updates available. Everything matches upstream.")
            return 0

        ts = int(time.time())

        print(f"Planned safe updates ({len(safe)}):")
        for d in sorted(safe, key=lambda x: x.path):
            print(f"  {d.path}")
        if conflicts:
            print()
            print(f"⚠ {len(conflicts)} user-modified files ALSO changed upstream:")
            for d in sorted(conflicts, key=lambda x: x.path):
                print(f"  {d.path}")
            print()
            if args.include_conflicts:
                print("  With --include-conflicts: each will be backed up as "
                      f".bak.{ts} and then overwritten.")
            else:
                print("  These are SKIPPED. Inspect them with `... diff <path>` "
                      "and re-run with --include-conflicts to adopt upstream anyway.")

        if not args.apply:
            print()
            print("Dry-run only. Re-run with --apply to make the changes.")
            return 0

        applied = 0
        backed = 0
        for d in safe:
            up_file = _upstream_path(next(r for r in manifest.files if r.path == d.path), up)
            if up_file is None or not up_file.is_file():
                continue
            _copy_and_rehash(up_file, dest / d.path, manifest, d.path)
            applied += 1

        if args.include_conflicts:
            for d in conflicts:
                rec = next(r for r in manifest.files if r.path == d.path)
                up_file = _upstream_path(rec, up)
                if up_file is None or not up_file.is_file():
                    continue
                local_file = dest / d.path
                bak = local_file.with_suffix(local_file.suffix + f".bak.{ts}")
                shutil.copy2(local_file, bak)
                backed += 1
                _copy_and_rehash(up_file, local_file, manifest, d.path)
                applied += 1

        # Refresh template/plugin SHAs on the manifest since upstream moved.
        manifest.template_sha = up.template_sha
        for p in manifest.plugins:
            p.sha = up.plugins_sha
        _write_manifest(manifest, manifest_path)

        print()
        print(f"✓ Applied: {applied}")
        if backed:
            print(f"✓ Backed up (conflicts): {backed}  (look for .bak.{ts})")
        print(f"✓ Manifest refreshed: {manifest_path.name}")
    return 0


def _copy_and_rehash(src: Path, dst: Path, manifest: Manifest, rel: str) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    new_sha = sha256_file(dst) or ""
    for r in manifest.files:
        if r.path == rel:
            r.sha256 = new_sha
            break


def _write_manifest(manifest: Manifest, path: Path) -> None:
    """Re-serialize manifest preserving the exact layout install.sh uses."""
    lines: list[str] = []
    lines.append("# Tracks what was installed so future tooling can diff against upstream.")
    lines.append("# Managed by install.sh / agent-system-updater — hand-edit only if you know what you are doing.")
    lines.append(f"manifest_version: {manifest.version}")
    lines.append("template:")
    lines.append(f"  source: {manifest.template_source}")
    lines.append(f"  sha: {manifest.template_sha}")
    lines.append("  installed_at: (unchanged — see previous manifest)")
    lines.append("plugins:")
    if not manifest.plugins:
        lines.append("  []")
    else:
        for p in manifest.plugins:
            lines.append(f"  - name: {p.name}")
            lines.append(f"    source: {p.source}")
            lines.append(f"    sha: {p.sha}")
            lines.append("    installed_at: (unchanged — see previous manifest)")
    lines.append("files:")
    if not manifest.files:
        lines.append("  []")
    else:
        for r in sorted(manifest.files, key=lambda x: x.path):
            lines.append(f"  - path: {r.path}")
            lines.append(f"    origin: {r.origin}")
            lines.append(f"    sha256: {r.sha256}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="agent_system_updater")
    parser.add_argument(
        "--project-root",
        default=None,
        help="Project root (defaults to CWD). Must contain .agent-system-manifest.yaml.",
    )

    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check-updates", help="Summarize what has changed upstream.")

    diff_p = sub.add_parser("diff", help="Show unified diff for one path.")
    diff_p.add_argument("path", help="Path (as recorded in manifest) to diff.")

    update_p = sub.add_parser("update", help="Apply upstream changes.")
    update_p.add_argument("--apply", action="store_true",
                          help="Make the changes (default is dry-run).")
    update_p.add_argument("--include-conflicts", action="store_true",
                          help="Also adopt upstream for files you modified locally "
                          "(backs up your version as .bak.<ts>).")

    args = parser.parse_args(argv)

    handlers = {
        "check-updates": cmd_check,
        "diff": cmd_diff,
        "update": cmd_update,
    }
    return handlers[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
