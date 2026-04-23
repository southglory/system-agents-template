# Contributing to system-agents-template

Thanks for wanting to improve the template. This repo holds the bootstrap
pieces every system-agents project starts from: the installer, the
`recruiter` agent, the turn-bot, the chatroom/board conventions, and the
update tooling. **Domain-specific work belongs in `system-agents-plugins` instead**
— see that repo's [`CONTRIBUTING.md`](https://github.com/southglory/system-agents-plugins/blob/main/CONTRIBUTING.md) for the plugin layout rules.

## Quick start for contributors

```bash
git clone https://github.com/southglory/system-agents-template.git
cd system-agents-template

# Installer lint + syntax
bash -n install.sh

# Updater unit tests (stdlib only, no extra install step)
python -m pytest bot/tests/ -v
```

CI runs the same checks on every PR plus a live smoke-install against the
real plugins repo, so your PR will exercise a full end-to-end flow.

## What belongs here vs in plugins

| It belongs in `system-agents-template` if… | It belongs in `system-agents-plugins` if… |
|---|---|
| It's used by **every** project regardless of domain | It's specific to one domain (Discord, Unity, etc.) |
| It changes `install.sh`, the manifest schema, or the update tooling | It adds slash commands for a specific external service |
| It changes the turn-based protocol (chatrooms, PROTOCOL.md, tasks/board.yaml) | It adds an agent role that only makes sense for one team |
| It adds a skill that's domain-neutral (check-chatroom, send-message, …) | It adds a skill that talks to a specific API |

When in doubt, open an issue first so we can decide together.

## House rules

1. **Two-question install UX is load-bearing.** Any change to `install.sh`
   must keep the interactive run limited to the existing pair of prompts
   (location, plugin selection). Everything else belongs behind a CLI flag.
2. **Don't touch users' `.gitignore`.** Runtime directories self-isolate
   (`.system-agents/<plugin>/.gitignore: *`). If a change would require
   editing the host project's root `.gitignore`, find another approach.
3. **Manifest is append-only in spirit.** Schema changes must bump
   `manifest_version` and `bot/agent_system_updater.py` must understand
   both the old and the new shape during a deprecation window.
4. **Seven-locale README.** `README.md` is the master; any user-facing
   change that lands there must also land in the other six locale files
   (`ko / zh / ja / es / de / fr`). The PR template reminds you.
5. **Bash 3.2 portability.** `install.sh` runs on macOS default Bash
   (3.2). Don't use `mapfile`, fancy `[[ =~ ]]` features, or process
   substitution that assumes Bash 4+ without testing it. Our CI install
   job runs on `macos-latest`, which catches most regressions
   automatically.
6. **No secrets in tests or fixtures.** If a test needs a Discord-like
   token, synthesize a fake string; never paste a real token anywhere.

## Scope of a good PR

- One concern per PR. "Fix install.sh on macOS" + "add new skill" + "add
  CONTRIBUTING.md" is three PRs, not one.
- Touch no more files than the change needs. README updates count as part
  of the change (don't land code without the docs).
- Tests follow the code. A new branch in `agent_system_updater` without a
  matching test is a red flag; reviewers will ask for one.

## Releasing

Version tags move the public Release asset. Concretely:

1. Bump the version reference in user-facing docs (if any).
2. Tag `vX.Y.Z` on `main`.
3. Push the tag. The `release` workflow attaches `install.sh` and
   `docs/INSTALL.md` to a new GitHub Release named `vX.Y.Z` automatically.

This keeps the rolling URL (`raw.githubusercontent.com/.../main/install.sh`)
and the pinned URL (`releases/latest/download/install.sh`) both valid — see
the One-line install blocks in the locale READMEs.

## License

MIT — see [`LICENSE`](LICENSE).

---

For plugin contributions (new plugins, Discord-huddle features, etc.),
switch to [`system-agents-plugins`](https://github.com/southglory/system-agents-plugins).
