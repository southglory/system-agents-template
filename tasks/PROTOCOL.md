# 작업 관리 프로토콜

## 구조

```
tasks/
├── PROTOCOL.md          ← 이 문서
├── board.yaml           ← 작업 보드 (전체 작업 목록)
├── backlog/             ← 아직 시작 안 한 작업의 상세 파일
├── active/              ← 진행 중인 작업의 상세 파일
└── done/                ← 완료된 작업의 상세 파일
```

## board.yaml

모든 작업은 `board.yaml` 한 파일에서 관리한다. 목표 → 단계 → 작업의 계층 구조.

### 전체 형식

```yaml
- goal: 목표 제목
  owner: 책임자
  start: YYYY-MM-DD
  due: YYYY-MM-DD
  status: 진행          # 대기 / 진행 / 완료

  phases:
    - phase: 단계 제목
      tasks:
        - title: 작업 제목
          type: feature       # bug / feature / improvement / docs
          priority: medium    # high / medium / low
          created_by: 요청자
          assignee: 담당자
          start: YYYY-MM-DD
          due: YYYY-MM-DD
          done: null          # 완료 시 YYYY-MM-DD
          status: 대기        # 대기 / 진행 / 완료
          notes: |
            작업 관련 메모
```

### 필드 설명

| 필드 | 필수 | 설명 |
|------|------|------|
| title | O | 작업 제목 |
| type | O | 작업 종류: `bug`, `feature`, `improvement`, `docs` |
| priority | O | 긴급도: `high`, `medium`, `low` |
| created_by | O | 작업을 요청한 사람 |
| assignee | O | 현재 담당자 |
| start | - | 실제 착수일 |
| due | - | 마감일 |
| done | - | 완료일 (완료 시 기입) |
| status | O | `대기`, `진행`, `완료` |
| notes | - | 메모, 이슈, 배경 등 자유 기술 |

## 상태 흐름

```
대기 → 진행 → 완료
```

- **대기**: 할 일이 정해졌지만 아직 시작 안 함
- **진행**: 작업 중. `start` 기입
- **완료**: 끝남. `done` 기입, status를 `완료`로 변경

## 작업 파일 (선택)

작업별 상세 내용이 많을 때 별도 파일을 둘 수 있다.

```
active/
└── 알림-발송-중복-버그.md
```

```markdown
---
title: 알림 발송 중복 버그
ref: board.yaml의 해당 작업
---

## 상세 내용
동일 이벤트에 알림이 2~3회 발송되는 현상.

## 대화
### Bob | 2026-03-17 15:00
원인 파악함. 이벤트 큐 중복 처리 문제.

### Alice | 2026-03-17 16:00
우선 진행할 것.
```

- `board.yaml`이 전체 현황 요약 (스프레드시트 역할)
- 개별 파일은 상세 논의가 필요할 때만 생성

## 채팅방 연동

채팅 메시지에서 작업을 참조할 때 `task` 필드 사용:

```markdown
---
from: bob
to: all
task: 알림 발송 중복 버그
subject: 원인 파악 완료
---
```

## 운영 규칙

- `board.yaml`은 누구나 수정 가능하되, 자기 담당 작업 위주로 업데이트
- 상태 변경 시 `start`/`done` 날짜를 반드시 기입
- 에이전트당 동시 진행(`진행` 상태) 작업은 최대 3개
- 완료된 goal은 주기적으로 정리 (goal 통째로 삭제하거나 아카이브)
