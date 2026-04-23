"""Tests for agent_system_updater.py.

These exercise the core logic — manifest parsing, sha-based comparison,
unified-diff output — without hitting the network. We build a tiny
synthetic "project" + "upstream" in a tmp_path and let the updater loose
on it.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
BOT_DIR = HERE.parent
if str(BOT_DIR) not in sys.path:
    sys.path.insert(0, str(BOT_DIR))

from agent_system_updater import (
    Manifest,
    FileRecord,
    parse_manifest,
    sha256_file,
    compare,
    Upstream,
)


def _write(path: Path, content: str) -> None:
    """Write content as bytes to avoid Windows lineending translation."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content.encode("utf-8"))


def _sha(content: str) -> str:
    """sha256 of content as UTF-8 bytes (no lineending translation)."""
    import hashlib
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _make_manifest_file(path: Path, records: list[tuple[str, str, str]]) -> None:
    """records: list of (rel_path, origin, sha256)."""
    lines = [
        "# test manifest",
        "manifest_version: 2",
        "template:",
        "  source: https://github.com/example/template.git",
        "  sha: abcdef123456",
        "  installed_at: 2026-01-01T00:00:00Z",
        "plugins:",
        "  - name: demo",
        "    source: https://github.com/example/plugins.git",
        "    sha: 123456abcdef",
        "    installed_at: 2026-01-01T00:00:00Z",
        "files:",
    ]
    for p, o, s in records:
        lines.append(f"  - path: {p}")
        lines.append(f"    origin: {o}")
        lines.append(f"    sha256: {s}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_parse_manifest_v2(tmp_path):
    mf = tmp_path / ".agent-system-manifest.yaml"
    _make_manifest_file(mf, [
        ("bot/main.py", "template", _sha("x")),
        ("bot/ext.py", "plugin:demo", _sha("y")),
    ])
    m = parse_manifest(mf)
    assert m.version == 2
    assert m.template_source == "https://github.com/example/template.git"
    assert m.template_sha == "abcdef123456"
    assert len(m.plugins) == 1
    assert m.plugins[0].name == "demo"
    assert len(m.files) == 2
    assert {(f.path, f.origin) for f in m.files} == {
        ("bot/main.py", "template"),
        ("bot/ext.py", "plugin:demo"),
    }


def test_parse_manifest_missing_fails(tmp_path):
    with pytest.raises(SystemExit):
        parse_manifest(tmp_path / "nope.yaml")


def test_sha256_file_roundtrip(tmp_path):
    p = tmp_path / "x.txt"
    p.write_text("hello\n", encoding="utf-8")
    assert sha256_file(p) is not None
    assert sha256_file(tmp_path / "nonexistent") is None


def _make_upstream(tmp_path, files: dict[str, str]) -> Upstream:
    """Build an Upstream object pointing at a fake template repo with given files."""
    template_dir = tmp_path / "upstream-template"
    for rel, content in files.items():
        _write(template_dir / rel, content)
    plugins_dir = tmp_path / "upstream-plugins"
    plugins_dir.mkdir(exist_ok=True)
    return Upstream(
        template_dir=template_dir,
        template_sha="upstream123",
        plugins_dir=plugins_dir,
        plugins_sha="plug456",
        plugin_subpaths={"demo": "demo/"},
    )


def test_compare_untouched_unchanged(tmp_path):
    """Local matches manifest AND upstream — no diff to report."""
    dest = tmp_path / "proj"
    dest.mkdir()
    content = "original contents\n"
    _write(dest / "a.txt", content)
    sha = _sha(content)

    mf = dest / ".agent-system-manifest.yaml"
    _make_manifest_file(mf, [("a.txt", "template", sha)])
    manifest = parse_manifest(mf)

    up = _make_upstream(tmp_path, {"a.txt": content})  # upstream same as local
    diffs = compare(manifest, dest, up)

    assert len(diffs) == 1
    assert diffs[0].local_status == "untouched"
    assert diffs[0].upstream_status == "same"


def test_compare_safe_update_available(tmp_path):
    """Local == manifest sha, but upstream has moved to new content."""
    dest = tmp_path / "proj"
    dest.mkdir()
    original = "v1 contents\n"
    _write(dest / "a.txt", original)
    sha = _sha(original)

    mf = dest / ".agent-system-manifest.yaml"
    _make_manifest_file(mf, [("a.txt", "template", sha)])
    manifest = parse_manifest(mf)

    up = _make_upstream(tmp_path, {"a.txt": "v2 contents\n"})
    diffs = compare(manifest, dest, up)

    assert diffs[0].local_status == "untouched"
    assert diffs[0].upstream_status == "changed"


def test_compare_conflict(tmp_path):
    """User modified locally AND upstream moved."""
    dest = tmp_path / "proj"
    dest.mkdir()
    _write(dest / "a.txt", "user edited\n")  # differs from manifest

    original_sha = _sha("original\n")

    mf = dest / ".agent-system-manifest.yaml"
    _make_manifest_file(mf, [("a.txt", "template", original_sha)])
    manifest = parse_manifest(mf)

    up = _make_upstream(tmp_path, {"a.txt": "upstream new\n"})
    diffs = compare(manifest, dest, up)

    assert diffs[0].local_status == "user-modified"
    assert diffs[0].upstream_status == "changed"


def test_compare_user_modified_but_upstream_unchanged(tmp_path):
    """User edited locally; upstream still has the original. No update,
    no conflict — just user's own edit."""
    dest = tmp_path / "proj"
    dest.mkdir()
    _write(dest / "a.txt", "user edited\n")

    original = "original\n"
    original_sha = _sha(original)

    mf = dest / ".agent-system-manifest.yaml"
    _make_manifest_file(mf, [("a.txt", "template", original_sha)])
    manifest = parse_manifest(mf)

    up = _make_upstream(tmp_path, {"a.txt": original})
    diffs = compare(manifest, dest, up)

    assert diffs[0].local_status == "user-modified"
    assert diffs[0].upstream_status == "same"


def test_compare_locally_missing(tmp_path):
    """File recorded in manifest but gone from disk."""
    dest = tmp_path / "proj"
    dest.mkdir()
    # No file written
    original_sha = _sha("original\n")

    mf = dest / ".agent-system-manifest.yaml"
    _make_manifest_file(mf, [("a.txt", "template", original_sha)])
    manifest = parse_manifest(mf)

    up = _make_upstream(tmp_path, {"a.txt": "original\n"})
    diffs = compare(manifest, dest, up)

    assert diffs[0].local_status == "missing"


def test_compare_upstream_removed(tmp_path):
    """File was in manifest but is gone from upstream now."""
    dest = tmp_path / "proj"
    dest.mkdir()
    content = "original\n"
    _write(dest / "a.txt", content)
    sha = _sha(content)

    mf = dest / ".agent-system-manifest.yaml"
    _make_manifest_file(mf, [("a.txt", "template", sha)])
    manifest = parse_manifest(mf)

    up = _make_upstream(tmp_path, {})  # upstream has nothing
    diffs = compare(manifest, dest, up)

    assert diffs[0].upstream_status == "removed"


def test_plugin_path_mapping(tmp_path):
    """plugin:<name> origin should route through plugins repo + plugin_subpaths."""
    dest = tmp_path / "proj"
    dest.mkdir()
    content = "plugin file\n"
    _write(dest / "bot/foo.py", content)  # merged into DEST root
    sha = _sha(content)

    mf = dest / ".agent-system-manifest.yaml"
    _make_manifest_file(mf, [("bot/foo.py", "plugin:demo", sha)])
    manifest = parse_manifest(mf)

    # Upstream plugin file lives at <plugins_repo>/demo/bot/foo.py
    plugins_dir = tmp_path / "upstream-plugins"
    _write(plugins_dir / "demo/bot/foo.py", content)  # matches local
    up = Upstream(
        template_dir=tmp_path / "upstream-template",
        template_sha="t",
        plugins_dir=plugins_dir,
        plugins_sha="p",
        plugin_subpaths={"demo": "demo/"},
    )
    diffs = compare(manifest, dest, up)
    assert diffs[0].upstream_status == "same"

    # Now change upstream
    _write(plugins_dir / "demo/bot/foo.py", "plugin file v2\n")
    diffs = compare(manifest, dest, up)
    assert diffs[0].upstream_status == "changed"


def test_plugin_docs_path_mapping(tmp_path):
    """Plugin files copied to DEST/plugins/<name>/... should map back to
    <plugins_repo>/<name>/..."""
    dest = tmp_path / "proj"
    dest.mkdir()
    content = "plugin readme\n"
    _write(dest / "plugins/demo/README.md", content)
    sha = _sha(content)

    mf = dest / ".agent-system-manifest.yaml"
    _make_manifest_file(mf, [("plugins/demo/README.md", "plugin:demo", sha)])
    manifest = parse_manifest(mf)

    plugins_dir = tmp_path / "upstream-plugins"
    _write(plugins_dir / "demo/README.md", content)
    up = Upstream(
        template_dir=tmp_path / "upstream-template",
        template_sha="t",
        plugins_dir=plugins_dir,
        plugins_sha="p",
        plugin_subpaths={"demo": "demo/"},
    )
    diffs = compare(manifest, dest, up)
    assert diffs[0].upstream_status == "same"
