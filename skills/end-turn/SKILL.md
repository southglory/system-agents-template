---
name: end-turn
description: 현재 에이전트의 턴을 종료한다.
---

# 턴 종료

1. `/send-message general`로 턴 종료 메시지를 보낸다:
   - type: `turn-end`
   - subject: "{에이전트이름} 턴 종료"
   - 본문: 이번 턴에서 한 일 한줄 요약

2. 사용자에게 "턴 종료. 다음 에이전트로 넘겨주세요." 라고 알린다.
