# 작업 관리 프로토콜

## 핵심 원칙

> **board.yaml은 봇만 쓸 수 있다. 에이전트는 읽기만 한다.**
>
> 에이전트가 작업을 생성/변경/완료하려면 채팅방에 해당 type의 메시지를 보내야 한다.
> 봇이 메시지를 읽고 board.yaml을 자동 업데이트한다.

## 구조

```
tasks/
├── PROTOCOL.md          ← 이 문서
└── board.yaml           ← 작업 보드 (봇만 쓰기 가능)
```

## 턴제 라운드

에이전트들은 순차적으로 실행된다. 한 라운드는 5개 Phase로 구성된다.

```
=== 라운드 N ===

[Phase 1: 봇] board.yaml 업데이트
  - 이전 라운드의 메시지 스캔
  - task-create → 새 작업 등록 + ID 부여
  - task-update → 상태/담당자 변경
  - task-done → 완료 처리
  - 처리 결과를 general에 메시지로 알림

[Phase 2: 계획] (에이전트 순차 실행)
  에이전트 A →
    1. 채팅방 메시지 읽기
    2. board.yaml 확인 (읽기만)
    3. 이번 라운드에 할 작업을 task-claim 메시지로 선점
    4. 필요하면 task-create로 새 작업 요청
  에이전트 B →
    (동일 — A의 선점 메시지를 보고 판단)

[Phase 3: 봇] board.yaml 업데이트
  - task-claim 반영 (assignee + status 변경)
  - task-create 반영 (ID 부여)
  - 충돌 시 먼저 보낸 메시지 우선 (파일명 시간순)

[Phase 4: 실행] (에이전트 순차 실행)
  에이전트 A →
    1. board.yaml에서 자기 담당 확인
    2. 실제 작업 수행 (코드 작성, 문서 작성 등)
    3. 결과를 채팅방에 메시지로 공유
    4. 완료 시 task-done 메시지 전송
  에이전트 B →
    (동일)

[Phase 5: 봇] board.yaml 업데이트
  - task-done 반영
  - task-update 반영

=== 라운드 N+1 ===
```

## 작업 ID

- 봇이 task-create 메시지를 처리할 때 자동 부여
- 형식: `T-001`, `T-002`, ... (전역 순번)
- board.yaml의 각 작업에 `id` 필드로 기록
- 이후 task-update, task-done, task-claim에서 `ref` 필드로 참조

## board.yaml

### 형식

```yaml
last_updated: "2026-03-19 14:35:00 UTC"
next_id: 3

tasks:
  - id: T-001
    title: 사용자 인증 API 리팩토링
    goal: 대시보드 v2 출시
    phase: 백엔드 API 개편
    type: improvement
    priority: high
    created_by: alice
    assignee: bob
    start: 2026-03-10
    due: 2026-03-18
    done: 2026-03-17
    status: 완료

  - id: T-002
    title: 차트 컴포넌트 교체
    goal: 대시보드 v2 출시
    phase: 프론트엔드 UI 개편
    type: improvement
    priority: medium
    created_by: alice
    assignee: charlie
    start: 2026-03-15
    due: 2026-03-24
    done: null
    status: 진행
    notes: |
      recharts → visx 전환. 커스텀 툴팁 필요.
```

### 필드 설명

| 필드 | 필수 | 설명 |
|------|------|------|
| id | O | 봇이 자동 부여 (T-001 형식) |
| title | O | 작업 제목 |
| goal | O | 소속 목표 |
| phase | O | 소속 단계 |
| type | O | `bug`, `feature`, `improvement`, `docs` |
| priority | O | `high`, `medium`, `low` |
| created_by | O | 작업을 요청한 에이전트 |
| assignee | O | 현재 담당자 |
| start | - | 실제 착수일 |
| due | O | 마감일 |
| done | - | 완료일 (완료 시 기입) |
| status | O | `대기`, `진행`, `완료` |
| notes | - | 메모 |

### 메타 필드

| 필드 | 설명 |
|------|------|
| last_updated | 봇이 마지막으로 업데이트한 시각 |
| next_id | 다음에 부여할 작업 ID 번호 |

## 상태 흐름

```
대기 → 진행 → 완료
```

- **대기**: task-create로 등록됨. 아직 아무도 선점하지 않음
- **진행**: task-claim 또는 task-update로 누군가 착수함. `start` 기입
- **완료**: task-done으로 완료 보고됨. `done` 기입

## 에이전트 행동 규칙

### 할 수 있는 것
- board.yaml 읽기
- task-create 메시지 보내기 (새 작업 요청)
- task-claim 메시지 보내기 (Phase 2에서 작업 선점)
- task-update 메시지 보내기 (상태 변경 요청)
- task-done 메시지 보내기 (완료 보고)

### 할 수 없는 것
- **board.yaml 직접 수정**
- Phase 2에서 실제 작업 수행
- Phase 4에서 task-claim

### 선점 충돌

같은 작업을 두 에이전트가 claim할 경우:
- 파일명 시간순으로 먼저 보낸 쪽이 우선
- 봇이 나중 claim은 무시하고 해당 에이전트에게 알림

## 운영 규칙

- 에이전트당 동시 진행 작업은 최대 3개
- 완료된 작업은 봇이 주기적으로 정리
