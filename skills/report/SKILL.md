---
name: report
description: 이번 턴의 작업 결과를 관련 채팅방에 자동으로 공유한다.
---

# 작업 결과 보고

## 절차

1. 이번 턴에서 수행한 작업을 정리한다.

2. 각 작업에 대해 적절한 메시지를 `/send-message`로 전송한다:
   - 완료한 작업 → `task-done`을 `general`에
   - 진행 중인 작업 → `task-update`를 `general`에
   - 특정 에이전트와 관련된 내용 → 해당 1:1 채팅방에 `message`로

3. 사용자에게 보고 내역을 요약해서 알린다.
