# 에이전트 간 채팅 프로토콜

## Quick Reference — 메시지 타입별 필수 필드

> **일괄 등록 지원.** `task-create`는 frontmatter로 1개, 또는 body에 YAML 리스트로 여러 태스크를 한 번에 등록할 수 있다. (아래 일괄 등록 참조)

| type | 필수 frontmatter 필드 | 비고 |
|------|----------------------|------|
| `message` | `from`, `to`, `time`, `type`, `subject` | |
| `task-create` | `from`, `to`, `time`, `type`, `subject` + 태스크 필드 | 일괄 등록: body에 YAML 리스트 가능 |
| `task-update` | `from`, `to`, `time`, `type`, `subject`, **`ref`** | ⚠️ `ref` 없으면 봇이 태스크를 찾지 못함 |
| `task-done` | `from`, `to`, `time`, `type`, `subject`, **`ref`** | ⚠️ `ref` 없으면 완료 처리 불가 |
| `task-claim` | `from`, `to`, `time`, `type`, `subject`, **`ref`** | ⚠️ `ref` 없으면 선점 불가. Phase 2 전용 |
| `turn-end` | `from`, `to`, `time`, `type`, `subject` | |

> **`ref`는 봇이 태스크를 식별하는 유일한 키다.** `task-update`, `task-done`, `task-claim`에서 `ref`를 빠뜨리면 봇이 아무 처리도 하지 못한다. 반드시 `ref: T-NNN` 형식으로 포함할 것.

---

## 구조

```
chatrooms/
├── PROTOCOL.md              ← 이 문서
├── .read-status/            ← 각 에이전트/봇의 마지막 읽은 메시지
│   └── {에이전트}.json
├── {에이전트A}-{에이전트B}/   ← 1:1 채팅방
└── general/                 ← 전체 공유 채널
```

## 메시지 파일 규칙

### 파일명
```
{날짜}_{시분초}_{에이전트명}.md
```
예: `2026-03-19_143052_alice.md`, `2026-03-19_143108_bob.md`

- 날짜와 시간은 UTC 기준
- 시분초는 6자리 연속 (HHMMSS)
- 에이전트명은 소문자
- **이 규칙으로 동시 작성 시 충돌을 방지한다**

### 메시지 형식

```markdown
---
from: {보내는 에이전트 이름 소문자}
to: {받는 에이전트 이름 소문자 또는 all}
time: {YYYY-MM-DD HH:MM:SS UTC}
type: {메시지 유형}
subject: {제목}
mentions: [{멘션할 에이전트 목록}]
attachments:
  - attachments/{메시지파일명}/{파일명}
---

{본문}
```

## 메시지 type

### message — 일반 대화
필수 필드: `from`, `to`, `time`, `type`, `subject`

```markdown
---
from: alice
to: all
time: 2026-03-19 14:30:52 UTC
type: message
subject: API 설계 논의
mentions: [bob]
---

@bob API 엔드포인트 구조 검토 부탁해.
```

### task-create — 작업 생성 요청

필수 필드: `from`, `to`, `time`, `type`, `subject`, `goal`, `phase`, `assignee`, `priority`, `due`

#### 단건 등록 (frontmatter에 태스크 정보 포함)

```markdown
---
from: alice
to: all
time: 2026-03-19 14:31:00 UTC
type: task-create
subject: 사용자 인증 API 리팩토링
goal: 대시보드 v2 출시
phase: 백엔드 API 개편
assignee: bob
priority: high
due: 2026-03-25
---

기존 레거시 인증 로직을 JWT 기반으로 전환.
```

#### 일괄 등록 (body에 YAML 리스트)

> body에 `tasks:` YAML 블록이 있으면 봇이 각각을 별도 태스크로 생성한다. frontmatter의 `goal`, `phase`, `assignee` 등은 리스트 내 항목이 생략한 필드의 기본값이 된다.

```markdown
---
from: alice
to: all
time: 2026-03-19 14:31:00 UTC
type: task-create
subject: 백엔드 API 개편 태스크 일괄 등록
goal: 대시보드 v2 출시
phase: 백엔드 API 개편
assignee: alice
priority: medium
---

tasks:
  - title: 사용자 인증 API 리팩토링
    assignee: bob
    priority: high
    due: 2026-03-25
  - title: 권한 체크 미들웨어 추가
    due: 2026-03-27
  - title: API 문서 갱신
    assignee: charlie
    due: 2026-03-28
```

#### `tasks:` 블록 뒤 자유 텍스트 가이드라인

봇은 `tasks:` YAML 리스트가 끝나는 지점을 "컬럼 0에서 시작하는 비-YAML 라인"으로 판단한다. 즉, 리스트 뒤에 **마크다운 헤더(`#`, `##`, …)로 시작하는 섹션**을 두면 그 지점에서 YAML 파싱이 깔끔하게 종료되고, 뒤의 자유 텍스트(우선순위 설명, 의존성 다이어그램, 참고 링크 등)는 봇이 무시한다.

**권장 패턴:**

```markdown
tasks:
  - title: task A
    due: 2026-03-25
  - title: task B

## 우선순위 & 의존성

- A는 독립 실행 가능
- B는 A 완료 후 착수
```

**주의 사항:**

- **반드시 `#`로 시작하는 헤더 또는 다른 컬럼 0 키로 블록을 끊을 것.** 그냥 빈 줄 + 평문을 이어 쓰면 YAML 파서가 해당 텍스트까지 읽으려다 실패하고, 봇은 "일괄 등록이 깨졌음"으로 판단하여 **단일 태스크 폴백**을 수행한다(경고 메시지가 함께 전송된다).
- 리스트 아이템의 들여쓰기는 일관되게 (스페이스 2개 권장). 탭/스페이스 혼용은 금지.
- `notes`처럼 여러 줄을 담고 싶으면 YAML 블록 스칼라(`|` 또는 `>`)를 사용한다.
- `tasks:`는 반드시 **컬럼 0**에서 시작해야 한다. 본문에 "the tasks: …"처럼 산문에 섞여 있으면 파싱되지 않는다(의도된 동작).

### task-update — 작업 상태/담당자 변경

> **⚠️ `ref` 필수.** `ref: T-NNN`이 없으면 봇이 대상 태스크를 찾지 못해 업데이트가 무시된다.

필수 필드: `from`, `to`, `time`, `type`, `subject`, `ref`

```markdown
---
from: bob
to: all
time: 2026-03-19 14:32:00 UTC
type: task-update
subject: 인증 API 작업 시작
ref: T-001
status: 진행
---

착수합니다. 3일 내 완료 예정.
```

### task-done — 작업 완료

> **⚠️ `ref` 필수.** `ref: T-NNN`이 없으면 봇이 대상 태스크를 찾지 못해 완료 처리가 되지 않는다.

필수 필드: `from`, `to`, `time`, `type`, `subject`, `ref`

```markdown
---
from: bob
to: all
time: 2026-03-22 10:00:00 UTC
type: task-done
subject: 인증 API 리팩토링 완료
ref: T-001
---

JWT 기반 인증으로 전환 완료. 테스트 통과.
```

### task-claim — 작업 선점 (Phase 2 전용)

> **⚠️ `ref` 필수.** `ref: T-NNN`이 없으면 봇이 대상 태스크를 찾지 못해 선점이 되지 않는다. Phase 4에서는 사용 금지.

필수 필드: `from`, `to`, `time`, `type`, `subject`, `ref`

```markdown
---
from: bob
to: all
time: 2026-03-19 14:30:52 UTC
type: task-claim
subject: T-003 작업 선점
ref: T-003
---

이번 라운드에서 T-003을 진행하겠습니다.
```

## 봇 메시지

봇은 `from: bot`으로 메시지를 보낸다.

```markdown
---
from: bot
to: all
time: 2026-03-19 14:35:00 UTC
type: message
subject: 작업 등록 완료
ref: T-005
---

@alice 요청한 작업이 등록되었습니다.
- ID: T-005
- 제목: 사용자 인증 API 리팩토링
- 담당: bob
- 마감: 2026-03-25
```

## 읽음 상태 관리

### .read-status/{agent}.json
```json
{
  "general": "2026-03-19_143052_alice.md",
  "alice-bob": "2026-03-19_120000_bob.md"
}
```

### 안 읽은 메시지 확인 방법

1. `.read-status/{내이름}.json`에서 해당 채팅방의 마지막 읽은 파일명 확인
2. 채팅방 디렉토리에서 그 파일 이후의 파일 목록 조회 (파일명 사전순 정렬)
3. 새 파일이 있으면 읽고, read-status 업데이트

## 멘션 규칙
- frontmatter의 `mentions` 필드에 알림 대상 에이전트 이름을 배열로 기입
- 본문에서 `@이름`으로 표시하여 가독성 확보
- 채팅방 확인 시 `mentions`에 자기 이름이 있으면 **우선 읽기** 대상
- 1:1 채팅방에서는 mentions 불필요

## 메시지 보내기

1. 해당 채팅방 디렉토리에 `{날짜}_{시분초}_{에이전트명}.md` 파일 생성
2. frontmatter에 필수 필드 기입 (type에 따라 다름)
3. 본문 작성
4. 자신의 read-status를 방금 쓴 파일로 업데이트

**에이전트는 반드시 `/send-message` 스킬로만 메시지를 작성한다.**

## 채팅방 네이밍

- 1:1: 이름을 알파벳순으로 연결 (예: `alice-bob`)
- 전체: `general`
- 새 채팅방: 필요 시 디렉토리 생성

## 첨부파일

### 구조
```
{채팅방}/
├── 2026-03-19_143052_alice.md
└── attachments/
    └── 2026-03-19_143052_alice/
        ├── screenshot.png
        └── result.jpg
```

### 규칙
- 첨부파일은 `attachments/{메시지파일명(확장자 제외)}/` 하위에 저장
- 메시지 frontmatter의 `attachments` 필드에 경로 목록 기재
- 이미지는 에이전트가 Read 도구로 직접 열어 확인 가능

## 주의사항

- 메시지 파일은 수정하지 않는다 (불변). 수정이 필요하면 새 메시지로 정정
- read-status는 자신의 것만 업데이트한다
- 긴급한 건 채팅방보다 사용자에게 직접 요청
- 첨부파일이 큰 경우 (영상 등) 경로만 공유하고 파일은 로컬에 유지
- **에이전트는 board.yaml을 직접 수정하지 않는다** — 작업 관련 변경은 반드시 task-* type 메시지로
