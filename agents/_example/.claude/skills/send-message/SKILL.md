---
name: send-message
description: 에이전트 간 채팅방에 메시지를 보낸다. 인자로 채팅방 이름을 받는다.
user_invocable: true
argument-hint: [채팅방이름 예: alice-bob]
---

# 채팅방에 메시지 보내기

채팅방: **$ARGUMENTS**

## 절차

1. 내 이름을 확인한다 (role.md 또는 현재 프로젝트 디렉토리에서 판단)

2. chatrooms 디렉토리를 찾는다. 현재 프로젝트의 상위에 `chatrooms/` 폴더가 있어야 한다.

3. 파일명을 결정한다.
   - 규칙: `{날짜}_{시분초}_{에이전트명}.md`
   - 날짜: UTC 기준 `YYYY-MM-DD`
   - 시분초: UTC 기준 `HHMMSS` (6자리)
   - 에이전트명: 소문자
   - 예: `2026-03-19_143052_alice.md`

4. 사용자에게 메시지 내용과 **type**을 확인한다 (대화 맥락에서 명확하면 바로 진행)

5. **type별 필수 필드를 검증한다:**

   | type | 필수 필드 |
   |------|-----------|
   | `message` | from, to, time, type, subject |
   | `task-create` | from, to, time, type, subject, goal, phase, assignee, priority, due |
   | `task-update` | from, to, time, type, subject, ref |
   | `task-done` | from, to, time, type, subject, ref |
   | `task-claim` | from, to, time, type, subject, ref |
   | `turn-end` | from, to, time, type, subject |

   - 필수 필드가 빠져 있으면 사용자에게 물어본다
   - **유효하지 않은 type이면 메시지를 보내지 않고 사용자에게 알린다**

6. type에 맞는 메시지 파일을 생성한다:

### message
```markdown
---
from: {내 이름}
to: {상대 또는 all}
time: {YYYY-MM-DD HH:MM:SS UTC}
type: message
subject: {제목}
mentions: [{멘션 대상}]
---

{본문}
```

### task-create
```markdown
---
from: {내 이름}
to: all
time: {YYYY-MM-DD HH:MM:SS UTC}
type: task-create
subject: {작업 제목}
goal: {소속 목표}
phase: {소속 단계}
assignee: {담당자}
priority: {high/medium/low}
due: {YYYY-MM-DD}
---

{상세 설명}
```

### task-update
```markdown
---
from: {내 이름}
to: all
time: {YYYY-MM-DD HH:MM:SS UTC}
type: task-update
subject: {변경 설명}
ref: {작업 ID, 예: T-001}
status: {변경할 상태}
---

{사유}
```

### task-done
```markdown
---
from: {내 이름}
to: all
time: {YYYY-MM-DD HH:MM:SS UTC}
type: task-done
subject: {완료 보고}
ref: {작업 ID}
---

{완료 내용 요약}
```

### task-claim
```markdown
---
from: {내 이름}
to: all
time: {YYYY-MM-DD HH:MM:SS UTC}
type: task-claim
subject: {작업 ID} 선점
ref: {작업 ID}
---

{선점 사유 또는 계획}
```

7. 자신의 `.read-status/{내이름}.json`을 업데이트하여 방금 보낸 파일을 마지막 읽은 것으로 기록한다.

8. 사용자에게 전송 완료를 알린다. type이 task-* 계열이면 "봇이 다음 Phase에서 처리합니다"라고 안내한다.
