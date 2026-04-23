#!/usr/bin/env bash
# install.sh — bootstrap a system-agents installation into the user's project.
#
# Questions asked: at most two — install location and plugin selection.
# Everything else follows sensible defaults. Use --yes for non-interactive.
#
# Usage:
#   ./install.sh                                             # interactive
#   ./install.sh --dest ~/my-proj/agent-system               # skip location prompt
#   ./install.sh --plugins discord-huddle                    # skip plugin prompt
#   ./install.sh --dest PATH --plugins NAME[,NAME...] --yes  # fully automatic
#   ./install.sh --plugins ""                                # install template only
#
# Flags:
#   --dest PATH          Target directory (must not exist unless --force).
#   --plugins LIST       Comma-separated plugin names from plugins.yaml. Empty = none.
#   --yes                Accept defaults, skip all prompts.
#   --force              Allow installing into an existing, non-empty directory.
#   --skills-global=MODE Copy skills to ~/.claude/skills/.
#                        MODE one of: backup (default) | overwrite | skip-existing | off.
#                          backup         — if an existing file differs, save it as
#                                           .bak.<ts> next to the original, then overwrite.
#                          overwrite      — always overwrite (old behavior).
#                          skip-existing  — never touch an existing skill file.
#                          off            — do not register skills globally at all.
#                        Accepts legacy values: true=backup, false=off.
#   --template-repo URL  Override upstream template source.
#   --plugins-repo URL   Override upstream plugins index source.
#   --help               Show this help.

set -euo pipefail

# ----- Configuration ---------------------------------------------------------

TEMPLATE_REPO_DEFAULT="https://github.com/southglory/system-agents-template.git"
PLUGINS_REPO_DEFAULT="https://github.com/southglory/system-agents-plugins.git"

DEST=""
PLUGINS_ARG=""         # empty string = "not set"; "," = "explicitly none"
ASSUME_YES=0
FORCE=0
SKILLS_GLOBAL_MODE=backup   # backup | overwrite | skip-existing | off
TEMPLATE_REPO="$TEMPLATE_REPO_DEFAULT"
PLUGINS_REPO="$PLUGINS_REPO_DEFAULT"

# Sentinels for "user typed nothing" vs "user typed empty string"
PLUGINS_SET=0

# ----- Helpers ---------------------------------------------------------------

die()  { printf 'error: %s\n' "$*" >&2; exit 1; }
info() { printf '%s\n' "$*"; }
ok()   { printf '✓ %s\n' "$*"; }

have() { command -v "$1" >/dev/null 2>&1; }

usage() {
    sed -n '2,22p' "$0" | sed 's/^# \{0,1\}//'
    exit 0
}

# ----- Argparse --------------------------------------------------------------

while [ $# -gt 0 ]; do
    case "$1" in
        --dest)              DEST="$2"; shift 2 ;;
        --dest=*)            DEST="${1#*=}"; shift ;;
        --plugins)           PLUGINS_ARG="$2"; PLUGINS_SET=1; shift 2 ;;
        --plugins=*)         PLUGINS_ARG="${1#*=}"; PLUGINS_SET=1; shift ;;
        --yes|-y)            ASSUME_YES=1; shift ;;
        --force)             FORCE=1; shift ;;
        --skills-global=*)   case "${1#*=}" in
                                 1|true|yes|backup) SKILLS_GLOBAL_MODE=backup ;;
                                 overwrite)         SKILLS_GLOBAL_MODE=overwrite ;;
                                 skip-existing)     SKILLS_GLOBAL_MODE=skip-existing ;;
                                 0|false|no|off)    SKILLS_GLOBAL_MODE=off ;;
                                 *) die "--skills-global: unknown mode ${1#*=} (expected backup|overwrite|skip-existing|off)" ;;
                             esac
                             shift ;;
        --template-repo)     TEMPLATE_REPO="$2"; shift 2 ;;
        --template-repo=*)   TEMPLATE_REPO="${1#*=}"; shift ;;
        --plugins-repo)      PLUGINS_REPO="$2"; shift 2 ;;
        --plugins-repo=*)    PLUGINS_REPO="${1#*=}"; shift ;;
        --help|-h)           usage ;;
        *)                   die "unknown argument: $1 (try --help)" ;;
    esac
done

# ----- Preflight -------------------------------------------------------------

have git    || die "git is required but not found on PATH"
have python || have python3 || die "python 3 is required but not found on PATH"
PY="$(command -v python3 || command -v python)"

# ----- Prompt: destination ---------------------------------------------------

if [ -z "$DEST" ]; then
    if [ "$ASSUME_YES" -eq 1 ]; then
        die "--yes requires --dest"
    fi
    default_dest="./agent-system"
    printf 'Install location [%s]: ' "$default_dest"
    read -r entered
    DEST="${entered:-$default_dest}"
fi

# Expand ~ manually (read -r doesn't)
case "$DEST" in
    "~")    DEST="$HOME" ;;
    "~/"*)  DEST="$HOME/${DEST#~/}" ;;
esac

# Existence check
if [ -e "$DEST" ]; then
    if [ -d "$DEST" ] && [ -z "$(ls -A "$DEST" 2>/dev/null)" ]; then
        : # empty dir is fine
    elif [ "$FORCE" -eq 1 ]; then
        info "warning: $DEST exists and is non-empty (--force), will overwrite file-by-file"
    else
        die "$DEST already exists and is not empty. Use --force to install into it."
    fi
fi

mkdir -p "$DEST"
DEST="$(cd "$DEST" && pwd)"   # absolutize

# ----- Fetch plugins index --------------------------------------------------

tmp_root="$(mktemp -d 2>/dev/null || mktemp -d -t systemagents)"
cleanup() { rm -rf "$tmp_root"; }
trap cleanup EXIT

info "Fetching plugin index..."
git clone --depth=1 --quiet "$PLUGINS_REPO" "$tmp_root/plugins-repo" \
    || die "failed to clone plugins repo: $PLUGINS_REPO"

plugins_yaml="$tmp_root/plugins-repo/plugins.yaml"
[ -f "$plugins_yaml" ] || die "plugins.yaml not found in $PLUGINS_REPO"

# Parse plugins.yaml via inline Python (avoids pyyaml dependency).
# Emit one tab-separated line per plugin: name<TAB>status<TAB>path<TAB>summary
parse_plugins() {
    "$PY" - "$plugins_yaml" <<'PYEOF'
import sys, re
path = sys.argv[1]
with open(path, "r", encoding="utf-8") as f:
    text = f.read()

# Hand-rolled micro-parser for the fixed schema; avoids a pyyaml dependency.
# Tolerant of blank lines, comments (#), and "- key: value" entries.
current = None
entries = []
for raw in text.splitlines():
    line = raw.rstrip()
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        continue
    if stripped == "plugins:":
        continue
    m = re.match(r"-\s+name:\s*(.+)$", stripped)
    if m:
        if current is not None:
            entries.append(current)
        current = {"name": m.group(1).strip().strip('"').strip("'")}
        continue
    m = re.match(r"([a-zA-Z_]+)\s*:\s*(.*)$", stripped)
    if m and current is not None:
        key, val = m.group(1), m.group(2).strip().strip('"').strip("'")
        if val:
            current[key] = val
if current is not None:
    entries.append(current)

for e in entries:
    print("\t".join([
        e.get("name", ""),
        e.get("status", "stable"),
        e.get("path", e.get("name", "") + "/"),
        e.get("summary", ""),
    ]))
PYEOF
}

# macOS ships Bash 3.2 (no mapfile). Use a read loop for portability.
PLUGIN_LINES=()
while IFS= read -r _line || [ -n "$_line" ]; do
    PLUGIN_LINES+=("$_line")
done < <(parse_plugins)

# ----- Prompt: plugin selection ----------------------------------------------

# Build selectable list (exclude "planned")
declare -a SELECTABLE_NAMES=()
declare -a SELECTABLE_SUMMARIES=()
declare -a SELECTABLE_PATHS=()
declare -a PLANNED_NAMES=()
for entry in "${PLUGIN_LINES[@]}"; do
    IFS=$'\t' read -r p_name p_status p_path p_summary <<<"$entry"
    [ -z "$p_name" ] && continue
    if [ "$p_status" = "planned" ]; then
        PLANNED_NAMES+=("$p_name")
    else
        SELECTABLE_NAMES+=("$p_name")
        SELECTABLE_SUMMARIES+=("$p_summary")
        SELECTABLE_PATHS+=("$p_path")
    fi
done

declare -a SELECTED=()

if [ "$PLUGINS_SET" -eq 1 ]; then
    # Honor --plugins (empty → no plugins)
    if [ -n "$PLUGINS_ARG" ]; then
        IFS=',' read -r -a requested <<<"$PLUGINS_ARG"
        for r in "${requested[@]}"; do
            r="$(printf '%s' "$r" | tr -d ' ')"
            [ -z "$r" ] && continue
            found=0
            for i in "${!SELECTABLE_NAMES[@]}"; do
                if [ "${SELECTABLE_NAMES[$i]}" = "$r" ]; then
                    SELECTED+=("$i")
                    found=1
                    break
                fi
            done
            [ $found -eq 1 ] || die "plugin not available: $r"
        done
    fi
elif [ "$ASSUME_YES" -eq 1 ]; then
    : # --yes without --plugins = no plugins selected
else
    info ""
    info "Available plugins:"
    if [ ${#SELECTABLE_NAMES[@]} -eq 0 ]; then
        info "  (none available)"
    else
        for i in "${!SELECTABLE_NAMES[@]}"; do
            printf '  %d) %s   %s\n' "$((i+1))" "${SELECTABLE_NAMES[$i]}" "${SELECTABLE_SUMMARIES[$i]}"
        done
    fi
    if [ ${#PLANNED_NAMES[@]} -gt 0 ]; then
        info "  (planned, not yet available: $(IFS=', '; echo "${PLANNED_NAMES[*]}"))"
    fi
    info ""
    printf 'Select plugins by number (comma-separated, empty = none): '
    read -r selection
    if [ -n "$selection" ]; then
        IFS=',' read -r -a picks <<<"$selection"
        for pick in "${picks[@]}"; do
            pick="$(printf '%s' "$pick" | tr -d ' ')"
            [ -z "$pick" ] && continue
            [[ "$pick" =~ ^[0-9]+$ ]] || die "not a number: $pick"
            idx=$((pick-1))
            [ $idx -ge 0 ] && [ $idx -lt ${#SELECTABLE_NAMES[@]} ] || die "out of range: $pick"
            SELECTED+=("$idx")
        done
    fi
fi

# ----- Install template ------------------------------------------------------

info ""
info "Installing template..."
git clone --depth=1 --quiet "$TEMPLATE_REPO" "$tmp_root/template-repo" \
    || die "failed to clone template repo: $TEMPLATE_REPO"

# Copy everything except the .git dir and the installer itself.
(
    cd "$tmp_root/template-repo"
    find . -mindepth 1 -maxdepth 1 \
        ! -name '.git' \
        ! -name 'install.sh' \
        -exec cp -R {} "$DEST/" \;
)
ok "Template files copied to $DEST"

# Ensure recruiter is present — it's the ticket to growing the team.
if [ ! -d "$DEST/agents/recruiter" ]; then
    if [ -d "$tmp_root/template-repo/agents/recruiter" ]; then
        cp -R "$tmp_root/template-repo/agents/recruiter" "$DEST/agents/"
        ok "Recruiter agent added"
    else
        info "warning: recruiter agent not found in template; you may need to create it manually"
    fi
else
    ok "Recruiter agent present"
fi

# ----- Install plugins -------------------------------------------------------

declare -a INSTALLED_PLUGIN_ENTRIES=()

if [ ${#SELECTED[@]} -gt 0 ]; then
    info ""
    info "Installing plugins..."
fi

# Helper: resolve upstream SHA of plugins repo for manifest.
plugins_sha="$(git -C "$tmp_root/plugins-repo" rev-parse --short=12 HEAD 2>/dev/null || echo unknown)"
template_sha="$(git -C "$tmp_root/template-repo" rev-parse --short=12 HEAD 2>/dev/null || echo unknown)"

for idx in "${SELECTED[@]}"; do
    p_name="${SELECTABLE_NAMES[$idx]}"
    p_path="${SELECTABLE_PATHS[$idx]}"
    src_dir="$tmp_root/plugins-repo/${p_path%/}"

    [ -d "$src_dir" ] || die "plugin path missing in repo: $p_path"

    # Merge plugin/bot into DEST/bot, plugin/skills into DEST/skills, etc.
    for sub in bot skills docs samples requirements.txt requirements-optional.txt requirements-dev.txt README.md; do
        src="$src_dir/$sub"
        [ -e "$src" ] || continue
        case "$sub" in
            docs|samples|README.md)
                dest_sub="$DEST/plugins/$p_name/$sub"
                mkdir -p "$(dirname "$dest_sub")"
                cp -R "$src" "$dest_sub"
                ;;
            *)
                # bot/, skills/, requirements*.txt merge into DEST root
                if [ -d "$src" ]; then
                    mkdir -p "$DEST/$sub"
                    cp -R "$src"/. "$DEST/$sub/"
                else
                    cp "$src" "$DEST/$sub"
                fi
                ;;
        esac
    done

    ok "Plugin: $p_name"
    INSTALLED_PLUGIN_ENTRIES+=("$p_name")

    # Copy sample .env files to .claude/secrets/ (with .example suffix preserved).
    if [ -d "$src_dir/samples" ]; then
        mkdir -p "$DEST/.claude/secrets"
        for sample in "$src_dir"/samples/*.example; do
            [ -e "$sample" ] || continue
            base="$(basename "$sample")"
            cp -n "$sample" "$DEST/.claude/secrets/$base"
        done
    fi
done

# ----- Register skills globally ----------------------------------------------
#
# User's ~/.claude/skills/ may already hold customized skills from prior
# installs or hand-edits. We never silently clobber them. Default mode is
# "backup": any existing file whose contents differ gets moved aside as
# `<file>.bak.<unix-ts>` before the new version is written. Identical files
# are left untouched (no spurious mtime churn). The summary at the end lists
# counts so the user can see exactly what happened.

if [ "$SKILLS_GLOBAL_MODE" != "off" ] && [ -d "$DEST/skills" ]; then
    target="$HOME/.claude/skills"
    mkdir -p "$target"

    backup_stamp="$(date +%s)"
    skills_new=0       # newly installed skill dir
    skills_same=0      # already present & identical (no-op)
    skills_backed=0    # existing & differing, backed up then replaced
    skills_skipped=0   # existing, skip-existing mode chose to leave them
    skills_overwritten=0
    declare -a backed_files=()

    for d in "$DEST/skills"/*/; do
        [ -d "$d" ] || continue
        name="$(basename "$d")"
        dst_dir="$target/$name"

        if [ ! -d "$dst_dir" ]; then
            cp -R "$d" "$target/"
            skills_new=$((skills_new + 1))
            continue
        fi

        # Skill directory already exists — decide per-file.
        while IFS= read -r -d '' src_file; do
            rel="${src_file#"$d"}"
            dst_file="$dst_dir/$rel"

            if [ ! -e "$dst_file" ]; then
                mkdir -p "$(dirname "$dst_file")"
                cp "$src_file" "$dst_file"
                continue
            fi

            if cmp -s "$src_file" "$dst_file"; then
                skills_same=$((skills_same + 1))
                continue
            fi

            case "$SKILLS_GLOBAL_MODE" in
                skip-existing)
                    skills_skipped=$((skills_skipped + 1))
                    ;;
                overwrite)
                    cp "$src_file" "$dst_file"
                    skills_overwritten=$((skills_overwritten + 1))
                    ;;
                backup)
                    mv "$dst_file" "${dst_file}.bak.${backup_stamp}"
                    cp "$src_file" "$dst_file"
                    skills_backed=$((skills_backed + 1))
                    backed_files+=("$name/$rel")
                    ;;
            esac
        done < <(find "$d" -type f -print0)
    done

    ok "Skills registered in $target (mode=$SKILLS_GLOBAL_MODE)"
    info "  new skill dirs: $skills_new   identical: $skills_same"
    case "$SKILLS_GLOBAL_MODE" in
        backup)
            info "  backed up (existing differed): $skills_backed"
            if [ "$skills_backed" -gt 0 ]; then
                info "  backup files saved as *.bak.${backup_stamp} next to originals:"
                for f in "${backed_files[@]}"; do info "    - $f"; done
            fi
            ;;
        overwrite)
            info "  overwritten: $skills_overwritten"
            ;;
        skip-existing)
            info "  skipped (existing differed, left alone): $skills_skipped"
            ;;
    esac
else
    info "Skills NOT registered globally (mode=off)"
fi

# ----- Manifest --------------------------------------------------------------
#
# Schema v2 adds per-file sha256 records so future tooling
# (/agent-system-check-updates, /agent-system-diff, /agent-system-update)
# can tell whether a local file is:
#   - identical to the upstream version recorded at install time (untouched),
#   - modified by the user since install (sha differs from manifest), or
#   - missing (present in manifest, not on disk).
#
# files: entries are keyed by path relative to DEST. origin tells us which
# upstream the file came from (template | plugin:<name>), so the updater
# can re-fetch the right source.

manifest_path="$DEST/.agent-system-manifest.yaml"
iso_now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# sha256 helper — prefer sha256sum (Linux), fall back to shasum -a 256 (macOS)
_sha256() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    else
        shasum -a 256 "$1" | awk '{print $1}'
    fi
}

# Build file records: each entry is "origin<TAB>relative_path<TAB>sha256".
# Origins:
#   template  = came from the template repo (copied in "Installing template..." step)
#   plugin:<name> = came from a specific plugin
# We determine origin by checking which source tree the path existed in.
declare -a FILE_RECORDS=()

_emit_files_for_origin() {
    local origin="$1"      # "template" or "plugin:<name>"
    local src_root="$2"    # source directory to compare paths against
    shift 2
    # Remaining args are the rel-path roots to scan inside src_root (e.g. bot skills agents).
    # Empty = scan everything.
    local rel
    while IFS= read -r -d '' f; do
        rel="${f#"$DEST/"}"
        # Skip manifest itself, secrets dir, and the auto-generated runtime gitignore files
        case "$rel" in
            .agent-system-manifest.yaml|.claude/secrets/*) continue ;;
        esac
        # Only record files whose path also exists in the source tree (i.e. came from this origin).
        # This lets template + plugin files be distinguished when plugins merge into DEST/bot etc.
        local src_candidate="$src_root/$rel"
        if [ -f "$src_candidate" ]; then
            local sha
            sha="$(_sha256 "$f")"
            FILE_RECORDS+=("$origin"$'\t'"$rel"$'\t'"$sha")
        fi
    done < <(find "$DEST" -type f -print0)
}

info ""
info "Recording file hashes for manifest..."

# Template origin first — this tags all files that came from the template repo.
_emit_files_for_origin "template" "$tmp_root/template-repo"

# Plugin files: emit per plugin. Because plugin bot/skills/requirements merge
# into DEST root, those paths will already have been tagged "template" if both
# trees contain same-named files. To keep the manifest unambiguous we re-tag
# any file whose contents match a plugin source as plugin-origin (overwriting
# the template tag). This handles the common case of plugins shipping
# requirements.txt that replaces the template's.
for idx in "${SELECTED[@]}"; do
    p_name="${SELECTABLE_NAMES[$idx]}"
    p_path="${SELECTABLE_PATHS[$idx]}"
    plugin_src="$tmp_root/plugins-repo/${p_path%/}"

    # Gather relative paths inside the plugin source tree (excluding docs/
    # samples/ README — those go to plugins/<name>/ in DEST and are already
    # picked up by the template-origin scan as NOT matching).
    declare -a plugin_files=()
    while IFS= read -r -d '' pf; do
        plugin_rel="${pf#"$plugin_src/"}"
        # Map plugin internal layout to DEST layout:
        # - bot/**, skills/**, requirements*.txt : merged into DEST root
        # - docs/**, samples/**, README*.md      : copied to DEST/plugins/<name>/
        case "$plugin_rel" in
            docs/*|samples/*|README.md|README.*.md)
                dest_rel="plugins/$p_name/$plugin_rel"
                ;;
            *)
                dest_rel="$plugin_rel"
                ;;
        esac
        dest_file="$DEST/$dest_rel"
        if [ -f "$dest_file" ]; then
            sha="$(_sha256 "$dest_file")"
            # Remove any existing record for this path (template or earlier plugin)
            # then append the plugin-tagged one. Simple linear filter is fine for
            # the record counts we deal with (<2k).
            declare -a _filtered=()
            for rec in "${FILE_RECORDS[@]}"; do
                IFS=$'\t' read -r _o _p _s <<<"$rec"
                [ "$_p" = "$dest_rel" ] && continue
                _filtered+=("$rec")
            done
            FILE_RECORDS=("${_filtered[@]}")
            FILE_RECORDS+=("plugin:$p_name"$'\t'"$dest_rel"$'\t'"$sha")
        fi
    done < <(find "$plugin_src" -type f -print0)
done

{
    printf '# Tracks what was installed so future tooling can diff against upstream.\n'
    printf '# Managed by install.sh — hand-edit only if you know what you are doing.\n'
    printf 'manifest_version: 2\n'
    printf 'template:\n'
    printf '  source: %s\n' "$TEMPLATE_REPO"
    printf '  sha: %s\n' "$template_sha"
    printf '  installed_at: %s\n' "$iso_now"
    printf 'plugins:\n'
    if [ ${#INSTALLED_PLUGIN_ENTRIES[@]} -eq 0 ]; then
        printf '  []\n'
    else
        for name in "${INSTALLED_PLUGIN_ENTRIES[@]}"; do
            printf '  - name: %s\n' "$name"
            printf '    source: %s\n' "$PLUGINS_REPO"
            printf '    sha: %s\n' "$plugins_sha"
            printf '    installed_at: %s\n' "$iso_now"
        done
    fi
    printf 'files:\n'
    if [ ${#FILE_RECORDS[@]} -eq 0 ]; then
        printf '  []\n'
    else
        # Sort records by path for deterministic output. Using a NUL-safe pipeline
        # so paths with spaces / tabs survive (unlikely in this tree but safe).
        _sorted=()
        while IFS= read -r _line || [ -n "$_line" ]; do
            _sorted+=("$_line")
        done < <(printf '%s\n' "${FILE_RECORDS[@]}" | sort -t$'\t' -k2,2)
        for rec in "${_sorted[@]}"; do
            IFS=$'\t' read -r _o _p _s <<<"$rec"
            printf '  - path: %s\n' "$_p"
            printf '    origin: %s\n' "$_o"
            printf '    sha256: %s\n' "$_s"
        done
    fi
} > "$manifest_path"
ok "Manifest written: $manifest_path"

# ----- Next steps ------------------------------------------------------------

info ""
info "Install complete."
info ""
info "Next:"
info "  1. cd $DEST/.."
info "  2. Start Claude Code and run /recruit to build your team."
if [ ${#INSTALLED_PLUGIN_ENTRIES[@]} -gt 0 ]; then
    info ""
    info "Plugin tokens to fill in $DEST/.claude/secrets/:"
    for name in "${INSTALLED_PLUGIN_ENTRIES[@]}"; do
        # Reassemble summary/needs info by re-reading plugins.yaml entries
        for i in "${!SELECTABLE_NAMES[@]}"; do
            if [ "${SELECTABLE_NAMES[$i]}" = "$name" ]; then
                needs=""
                # needs_token is the 5th field; re-parse
                needs="$(awk -v n="$name" '
                    /^  - name:/ { m = ($3 == n) }
                    m && /needs_token:/ { sub(/.*needs_token:[[:space:]]*/, ""); print; m=0 }
                ' "$plugins_yaml")"
                if [ -n "$needs" ]; then
                    info "  - $name: $needs"
                fi
                break
            fi
        done
    done
fi
