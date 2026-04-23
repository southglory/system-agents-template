---
name: agent-system-diff
description: 설치된 system-agents 파일 하나를 업스트림 버전과 unified diff로 비교한다
---

# Agent System — Diff

`/agent-system-diff <path>` 명령이 수행하는 작업.

## 동작

1. `.agent-system-manifest.yaml`에서 해당 파일의 기록 (origin, sha256) 을 찾는다.
2. 업스트림(template 또는 plugin:<name>)을 `git clone --depth=1`로 임시 fetch.
3. 로컬 파일과 업스트림 파일을 `difflib.unified_diff`로 비교하여 표준출력에 출력.

## 실행

```bash
python bot/agent_system_updater.py diff <path>
```

`<path>`는 매니페스트의 `path:` 값과 정확히 일치해야 한다 (보통 프로젝트 루트 상대경로).

예:

```bash
python bot/agent_system_updater.py diff bot/turn-bot.py
python bot/agent_system_updater.py diff skills/discord-huddle-post/SKILL.md
```

## 출력 예

```diff
--- local/bot/turn-bot.py
+++ upstream/bot/turn-bot.py
@@ -42,7 +42,7 @@
 def process_messages():
-    """Old docstring."""
+    """New docstring in upstream."""
     pass
```

## 쓰임새

`/agent-system-check-updates`가 알려준 **conflict** (local+upstream 둘 다 변경됨) 파일을 검토할 때. 업스트림이 어떻게 바뀌었는지 먼저 보고:

- 내 수정과 충돌하지 않는 변경이면 upstream을 그대로 수용
- 충돌하면 수동 병합 (3-way merge)

## 에러

- `no manifest record for path: X` — 오타 확인. 매니페스트에 기록된 정확한 경로를 사용한다. `/agent-system-check-updates`의 목록을 복사해 쓰는 것이 안전.
- `upstream copy ... is missing` — 업스트림에서 해당 파일이 삭제됐다는 뜻. 마이그레이션 필요.
- `local copy ... is missing` — 로컬에서 실수로 삭제됐거나 다른 경로로 이동. 복원하려면 `/agent-system-update --apply` 가 해결해준다 (untouched+missing은 안전하게 재설치됨).

## 의존성

- `git`, Python 3.10+ (stdlib만)
