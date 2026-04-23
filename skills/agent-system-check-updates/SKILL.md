---
name: agent-system-check-updates
description: 설치된 system-agents 템플릿/플러그인이 업스트림과 얼마나 벌어져 있는지 요약해서 보여준다
---

# Agent System — Check Updates

`/agent-system-check-updates` 명령이 수행하는 작업.

## 동작

1. 프로젝트 루트의 `.agent-system-manifest.yaml`을 읽는다 (install.sh가 생성한 파일 단위 sha256 기록).
2. 매니페스트에 기록된 업스트림 레포들(template + plugins)을 `git clone --depth=1`로 임시 fetch.
3. 각 기록 파일마다 세 값을 비교:
   - 매니페스트에 기록된 설치 시점 sha (= 설치 직후 상태)
   - 현재 로컬 파일의 sha (= 사용자가 수정했는지)
   - 현재 업스트림의 sha (= 새 릴리즈에서 바뀌었는지)
4. 결과를 네 버킷으로 분류해 사용자에게 요약:
   - **untouched + unchanged** — 아무 변화 없음 (대다수)
   - **untouched + upstream-moved** — 안전하게 업데이트 가능
   - **user-modified + unchanged** — 사용자가 수정한 파일. 업데이트 대상 아님
   - **user-modified + upstream-moved** — **충돌** (3-way 필요)

## 실행

Claude Code 세션에서 호출하면 에이전트가 다음을 수행한다:

```bash
python bot/agent_system_updater.py check-updates
```

필요 시 특정 프로젝트 루트 지정:

```bash
python bot/agent_system_updater.py --project-root /path/to/proj check-updates
```

## 출력 예

```
Manifest version:     2
Template installed:   939e9eb6b894  (https://github.com/southglory/system-agents-template.git)
Template upstream:    abcd12345678
Plugin discord-huddle installed: 8be892b80a8d  upstream: 05f7a9388373  (https://github.com/southglory/system-agents-plugins.git)

Total tracked files:          75
  untouched + unchanged:      70
  untouched + upstream-moved: 3  ← safe to update
  user-modified + unchanged:  1  ← your edits, no conflict
  user-modified + upstream-moved: 1  ← 3-way needed
  locally missing:            0
  removed upstream:           0

Safe updates available (3):
  - bot/turn-bot.py  [template]
  - skills/check-chatroom/SKILL.md  [template]
  - bot/discord_lib/storage.py  [plugin:discord-huddle]

⚠ Conflicts (1) — both you and upstream changed the same file:
  - agents/recruiter/CLAUDE.md  [template]
```

## 다음 단계

- `untouched + upstream-moved` 항목의 실제 변경을 보려면 `/agent-system-diff <path>`
- 안전한 업데이트만 반영하려면 `/agent-system-update`(기본 dry-run, `--apply` 로 실제 적용)
- 충돌 파일은 `diff`로 내용 확인 후 수동 병합 권장

## 의존성

- `git` (업스트림 clone)
- Python 3.10+ (stdlib만 사용, pyyaml 불필요)
- 네트워크 (업스트림 레포 접근)

## 에러

- `manifest not found` — install.sh로 먼저 설치한 적이 없는 프로젝트. 매니페스트가 없으면 이 스킬은 아무것도 비교할 수 없다.
- `failed to clone ...` — 네트워크 또는 레포 URL 변경. `.agent-system-manifest.yaml`의 `source:` 필드를 확인한다.
