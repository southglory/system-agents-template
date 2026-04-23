---
name: agent-system-update
description: 업스트림 변경 중 안전한 것만 반영하고, 충돌 파일은 건드리지 않거나 백업 후 적용한다
---

# Agent System — Update

`/agent-system-update` 명령이 수행하는 작업.

## 기본 동작: dry-run

인자 없이 호출하면 **아무것도 쓰지 않고** 계획만 출력한다.

```bash
python bot/agent_system_updater.py update
```

출력 예:

```
Planned safe updates (3):
  bot/turn-bot.py
  skills/check-chatroom/SKILL.md
  bot/discord_lib/storage.py

⚠ 1 user-modified files ALSO changed upstream:
  agents/recruiter/CLAUDE.md

  These are SKIPPED. Inspect them with `... diff <path>` and
  re-run with --include-conflicts to adopt upstream anyway.

Dry-run only. Re-run with --apply to make the changes.
```

## 실제 적용: `--apply`

안전한 업데이트만(= untouched + upstream-changed) 실제로 덮어쓴다. 사용자가 수정한 파일(user-modified)은 기본적으로 **건드리지 않는다**.

```bash
python bot/agent_system_updater.py update --apply
```

- 적용된 각 파일의 sha256 레코드를 매니페스트에 새 값으로 갱신
- `template.sha`, `plugins[].sha` 필드도 현재 업스트림 값으로 전진

## 충돌 파일도 강제로 수용: `--include-conflicts`

사용자가 수정했는데 업스트림도 바뀐 파일을 강제로 업스트림으로 맞추고 싶으면:

```bash
python bot/agent_system_updater.py update --apply --include-conflicts
```

각 충돌 파일은 덮어쓰기 전 **`<file>.bak.<unix-ts>`** 로 백업된다. 나중에 복구하거나 수동 병합 기준으로 쓸 수 있다.

## 적용 대상 분류 (check-updates와 동일)

- **Safe (adopt)**: `local=untouched` + `upstream=changed` — 내가 건드리지 않았고 업스트림만 바뀜. 충돌 없이 교체.
- **Conflicts (skip by default)**: `local=user-modified` + `upstream=changed` — 양쪽 다 바뀜. `--include-conflicts`가 있어야만 적용.
- **No-op**: `same` 또는 `user-modified+unchanged`. 조용히 넘김.
- **Missing locally**: 매니페스트에 있는데 로컬에 없음. 현재는 `update`가 건드리지 않음 (향후 `--restore-missing` 옵션 고려).

## 실행 흐름 요약

```
1. manifest + 업스트림 clone
2. compare() 로 diff 리스트 생성
3. dry-run: 계획만 출력
4. --apply: 안전한 항목 적용 + 매니페스트 sha 갱신
5. --include-conflicts: 위에 + 충돌 항목도 .bak 백업 후 덮어쓰기
```

## 지금 하지 않는 것

- **3-way 자동 병합**: 의도적으로 제공하지 않음. 충돌은 `/agent-system-diff`로 내용을 본 뒤 사용자가 수동으로 해결.
- **업스트림에서 제거된 파일 삭제**: `upstream=removed` 항목은 현재 리포트만 하고 로컬 파일을 지우진 않음. 중요한 파일을 실수로 잃을 위험을 피하기 위함.
- **Symlink/권한 유지**: `shutil.copy2`만 사용. 대다수 프로젝트에 충분.

## 의존성

- `git`, Python 3.10+ (stdlib만)

## 에러

- `manifest not found` — install.sh로 먼저 설치한 적이 없는 프로젝트.
- `failed to clone ...` — 네트워크 또는 레포 URL 변경.
- 파일 쓰기 실패 (퍼미션 등): stderr에 해당 경로 노출.
