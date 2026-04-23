# Installing system-agents

`install.sh` bootstraps the template into a project directory and optionally installs one or more plugins from `system-agents-plugins`. It asks at most two things (location, plugins) — everything else follows a default.

## Quick start

Interactive:

```bash
curl -sSL https://raw.githubusercontent.com/southglory/system-agents-template/main/install.sh | bash
```

Or clone first and run locally:

```bash
git clone https://github.com/southglory/system-agents-template.git
cd system-agents-template
./install.sh
```

Non-interactive (CI-friendly):

```bash
./install.sh --dest ~/my-proj/agent-system --plugins discord-huddle --yes
```

## What it does

1. Clones the template (shallow, no `.git`) into your chosen directory.
2. Ensures the `recruiter` agent is present — this is the agent that helps you build the rest of your team.
3. Loads the plugin index from the `system-agents-plugins` repo and lets you pick which to install.
4. Copies each selected plugin's `bot/`, `skills/`, `requirements*.txt` into the install root. `docs/`, `samples/`, and plugin-specific `README.md` go to `plugins/<name>/` for reference.
5. Copies skills to `~/.claude/skills/` so Claude Code picks up slash commands globally. Default mode is `backup`: if an existing skill file differs, it is saved as `<file>.bak.<unix-ts>` before the new version is written (identical files are left untouched). Use `--skills-global=skip-existing` to never modify existing skills, `overwrite` to always replace them, or `off` to not touch the global skills dir at all. A summary at the end of install lists how many files were new / identical / backed up.
6. Seeds `.claude/secrets/*.env.example` from each plugin's samples (you fill in real values afterward).
7. Writes `.agent-system-manifest.yaml` recording the template and plugin sources + commit SHAs. Future update tooling reads this file.

## Flags

| Flag | Effect |
|---|---|
| `--dest PATH` | Target directory. Required when `--yes` is used. |
| `--plugins LIST` | Comma-separated plugin names. Empty string (`--plugins ""`) = template only. |
| `--yes` / `-y` | Skip prompts; accept defaults. Requires `--dest`. |
| `--force` | Install into a non-empty directory (overwrites file-by-file). |
| `--skills-global=MODE` | How to handle `~/.claude/skills/` collisions. `backup` (default) / `overwrite` / `skip-existing` / `off`. `true` = `backup`, `false` = `off`. |
| `--template-repo URL` | Override upstream template source (useful for forks or mirrors). |
| `--plugins-repo URL` | Override upstream plugins index source. |
| `--help` | Show usage. |

## After install

1. `cd` into the parent project.
2. For each installed plugin that needs a token, fill `.claude/secrets/<plugin>.env` using the `.env.example` as a guide.
3. Open the project in Claude Code. Run `/recruit` — the recruiter agent walks you through adding project-specific agents (developer, designer, reviewer, etc.). During the conversation you can reference installed plugins' skills (`/discord-huddle-post`, etc.) so the new agents know how to use them.

## Manual install (no script)

If you prefer explicit steps:

```bash
# 1. Clone template
git clone --depth=1 https://github.com/southglory/system-agents-template.git /tmp/sat
cp -R /tmp/sat/. ~/my-proj/agent-system/
rm -rf ~/my-proj/agent-system/.git

# 2. (Optional) Clone plugins and copy the ones you want
git clone --depth=1 https://github.com/southglory/system-agents-plugins.git /tmp/sap
cp -R /tmp/sap/discord-huddle/bot/.    ~/my-proj/agent-system/bot/
cp -R /tmp/sap/discord-huddle/skills/. ~/my-proj/agent-system/skills/
cp /tmp/sap/discord-huddle/requirements.txt ~/my-proj/agent-system/

# 3. Register skills globally (so /discord-huddle-sync etc. work in Claude Code)
mkdir -p ~/.claude/skills
cp -R ~/my-proj/agent-system/skills/. ~/.claude/skills/

# 4. Seed env template
mkdir -p ~/my-proj/agent-system/.claude/secrets
cp /tmp/sap/discord-huddle/samples/discord-huddle.env.example \
   ~/my-proj/agent-system/.claude/secrets/
```

Manifest creation is skipped in this flow. Future update tooling assumes one exists, so if you plan to track upstream changes, running `install.sh` at least once is easier.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `git is required` | Install git (`apt`/`brew`/`winget`). |
| `python 3 is required` | Install Python 3.10+. |
| `{dest} already exists and is not empty` | Pick a new path, or pass `--force` to overlay. |
| `plugin not available: X` | Check `plugins.yaml` in `system-agents-plugins` — plugin may be `planned` (not selectable) or the name may be typo'd. |
| Fetching plugin index fails | Network issue or repo URL changed. Override with `--plugins-repo`. |
| Skills not appearing as slash commands | Ensure `~/.claude/skills/<skill-name>/SKILL.md` exists. Re-run with `--skills-global=true` if you opted out before. |

## What `install.sh` does not do

- Does not modify your project's root `.gitignore`. Runtime data dirs isolate themselves.
- Does not install Python packages. Run `pip install -r requirements.txt` (and `requirements-optional.txt` / `requirements-dev.txt` as needed) yourself.
- Does not check for or apply upstream updates on its own. Use the sibling skills instead once the manifest exists:
  - `/agent-system-check-updates` — summarize what changed upstream (untouched/user-modified × same/changed × 4 buckets)
  - `/agent-system-diff <path>` — show unified diff for one tracked file
  - `/agent-system-update` (dry-run) / `/agent-system-update --apply` — adopt safe updates; pass `--include-conflicts` to also overwrite locally-modified files (backed up as `.bak.<ts>`)

## Manifest schema

`.agent-system-manifest.yaml` uses version 2 (written by install.sh ≥ this release). It records:

- `template.source` + `template.sha` — where the template was cloned from and which commit
- `plugins[]` — same two fields per plugin, plus the `name`
- `files[]` — per-file `{path, origin, sha256}`. `origin` is either `template` or `plugin:<name>`.

The updater uses the sha256 field to decide whether a local file has been edited since install. Manual edits of the manifest are supported but discouraged; re-running `install.sh` rebuilds it from scratch.
