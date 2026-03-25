# System Agents Template

![GitHub stars](https://img.shields.io/github/stars/southglory/system-agents-template?style=social)
![GitHub forks](https://img.shields.io/github/forks/southglory/system-agents-template?style=social)
![GitHub license](https://img.shields.io/github/license/southglory/system-agents-template)

[English](README.md) | [한국어](README.ko.md) | [中文](README.zh.md) | [日本語](README.ja.md) | [Español](README.es.md) | [Deutsch](README.de.md) | [Français](README.fr.md)

Claude Code 기반 턴제 멀티 에이전트 운영 프레임워크.

각 에이전트가 독립적인 Claude Code 세션으로 동작하며, 채팅방을 통해 소통하고, 봇이 작업 보드를 자동 관리한다.

## 구조

```
system-agents/
├── agents/
│   ├── _example/              ← 에이전트 템플릿
│   │   ├── CLAUDE.md          ← 행동 규칙 (턴제 Phase별)
│   │   └── role.md            ← 역할 정의
│   └── {에이전트이름}/         ← 실제 에이전트
├── chatrooms/
│   ├── PROTOCOL.md            ← 채팅 프로토콜 (메시지 type 포함)
│   ├── .read-status/          ← 읽음 상태
│   └── general/               ← 전체 채널
├── tasks/
│   ├── PROTOCOL.md            ← 작업 관리 프로토콜
│   └── board.yaml             ← 작업 보드 (봇만 쓰기)
├── bot/
│   ├── turn-bot.py            ← 턴제 봇 스크립트
│   └── requirements.txt
├── skills/
│   ├── check-chatroom/        ← 안 읽은 메시지 확인
│   ├── check-mentions/        ← 멘션 확인
│   ├── send-message/          ← 메시지 보내기 (type 검증)
│   ├── end-turn/              ← 턴 종료
│   └── report/                ← 작업 결과 자동 공유
└── README.md
```

## 턴제 운영

에이전트들은 자유롭게 동시에 실행되지 않는다. **라운드** 단위로 순차 실행된다.

```
=== 라운드 N ===

[Phase 1: 봇]  board.yaml 업데이트 (이전 라운드 메시지 반영)

[Phase 2: 계획] (에이전트 순차 실행)
  각 에이전트 → 메시지 읽기 + 작업 선점(task-claim)

[Phase 3: 봇]  board.yaml 업데이트 (선점 반영)

[Phase 4: 실행] (에이전트 순차 실행)
  각 에이전트 → 실제 작업 수행 + 결과 메시지

[Phase 5: 봇]  board.yaml 업데이트 (결과 반영)

=== 라운드 N+1 ===
```

## 멀티 에이전트 호환성 (Claude & Antigravity)

이 템플릿은 **Claude Code**와 **Antigravity**(Google) 에이전트가 동시에 협업할 수 있도록 설계되었습니다.

- **Claude Code**: `.system-agents/`의 턴제 상태 관리와 `/skills/`를 통한 CLI 명령어 실행에 집중합니다.
- **Antigravity**: `.agents/workflows/`에 정의된 **터보(Turbo) 워크플로우**를 활용하여 고속 자동화 분석 및 구현을 수행합니다.
- **협업 방식**: 두 에이전트는 `board.yaml`(작업 보드)과 `chatrooms/`(이력)를 공유합니다. Antigravity는 작업을 시작하기 전 보드를 확인하여 턴제 프로토콜을 준수할 수 있습니다.

## 빠른 시작

### 1. 스킬 설치

```bash
cp -r skills/* ~/.claude/skills/
```

### 2. 에이전트 만들기

```bash
cp -r agents/_example agents/MyAgent
```

`role.md`에 역할, `CLAUDE.md`에 규칙을 작성한다.

### 3. 라운드 실행

```bash
# Phase 1: 봇
python bot/turn-bot.py

# Phase 2: 각 에이전트 계획 (자동 판단)
cd agents/AgentA && claude
cd agents/AgentB && claude

# Phase 3: 봇
python bot/turn-bot.py

# Phase 4: 각 에이전트 실행 (자동 판단)
cd agents/AgentA && claude
cd agents/AgentB && claude

# Phase 5: 봇
python bot/turn-bot.py
```

## 핵심 개념

### 에이전트
- 독립적인 Claude Code 세션으로 동작
- Phase 2에서 계획, Phase 4에서 실행
- board.yaml은 읽기만, 변경은 채팅 메시지로

### 채팅방
- 파일 기반 비동기 메시지 전달
- 메시지 type으로 일반 대화와 작업 지시를 구분
- 첨부파일 지원

### 메시지 type

| type | 용도 |
|------|------|
| `message` | 일반 대화 |
| `task-create` | 작업 생성 요청 |
| `task-update` | 상태/담당자 변경 |
| `task-done` | 작업 완료 보고 |
| `task-claim` | 작업 선점 (Phase 2) |
| `turn-end` | 턴 종료 |

### 봇
- board.yaml의 유일한 쓰기 권한자
- 채팅방 메시지(task-*)를 스캔하여 board.yaml 갱신
- task-create 시 ID(T-001) 부여 후 응답 메시지 전송

### 스킬
- `/check-chatroom {채팅방}` — 안 읽은 메시지 확인
- `/check-mentions` — 나를 멘션한 메시지 확인
- `/send-message {채팅방}` — 메시지 보내기 (type 검증 포함)
- `/end-turn` — 턴 종료
- `/report` — 작업 결과를 관련 채팅방에 자동 공유

## 시나리오: 라운드 플레이

Alice(프론트엔드)와 Bob(백엔드) 두 에이전트로 대시보드를 만드는 상황.

### Round 1

**Phase 1 — 봇**
```bash
$ python bot/turn-bot.py
[봇] 처리할 새 메시지 없음.
```
> 첫 라운드. 보드는 비어있다.

**Phase 2 — Alice의 턴 (계획)**
```
Alice : 채팅방 확인... 새 메시지 없음.
        보드 확인... 작업 없음.
        새 작업이 필요합니다.
사용자: 대시보드 만들어야 해. 너는 프론트엔드, Bob은 API.
Alice : task-create 2건 보내겠습니다.
        → [general] task-create "대시보드 UI 구현" assignee: alice
        → [general] task-create "대시보드 API 개발" assignee: bob
        /end-turn
```

**Phase 2 — Bob의 턴 (계획)**
```
Bob   : 채팅방 확인... Alice가 작업 2건 생성함.
        API 개발이 내 담당이군요. 봇이 ID 부여하면 claim하겠습니다.
        이번엔 할 게 없습니다.
        /end-turn
```

**Phase 3 — 봇**
```bash
$ python bot/turn-bot.py
[봇] 2개 메시지 처리 완료:
  [task-create] T-001 — 대시보드 UI 구현
  [task-create] T-002 — 대시보드 API 개발
```
> board.yaml에 T-001, T-002 등록됨. 봇이 general에 ID 알림.

**Phase 4 — Alice의 턴 (실행)**
```
Alice : 채팅방 확인... 봇이 T-001, T-002 등록 알림.
        보드 확인... T-001(대시보드 UI)이 내 담당, 상태: 대기.
        T-001 작업을 시작합니다.
        ... (React 컴포넌트 작성 중) ...
        UI 기본 구조 완성했습니다.
사용자: 공유해
Alice : /report
        → [general] task-update T-001 status: 진행 "기본 레이아웃 완성"
        → [alice-bob] message "API 엔드포인트 /api/stats 형태로 부탁해"
        /end-turn
```

**Phase 4 — Bob의 턴 (실행)**
```
Bob   : 채팅방 확인... Alice가 T-001 진행 중, API 형태 요청함.
        보드 확인... T-002(API 개발)이 내 담당, 상태: 대기.
        T-002 시작합니다. /api/stats 엔드포인트 포함해서.
        ... (FastAPI 엔드포인트 작성 중) ...
        API 완성했습니다.
        /report
        → [general] task-done T-002 "API 완성, /api/stats 포함"
        → [alice-bob] message "API 올렸어. /api/stats로 호출하면 돼"
        /end-turn
```

**Phase 5 — 봇**
```bash
$ python bot/turn-bot.py
[봇] 3개 메시지 처리 완료:
  [task-update] T-001 — 진행
  [task-done] T-002 — 완료
```

### Round 2

**Phase 1 — 봇**
```bash
$ python bot/turn-bot.py
[봇] 처리할 새 메시지 없음.
```

**Phase 2 — Alice의 턴**
```
Alice : 채팅방 확인... Bob이 API 완성, /api/stats 사용 가능.
        보드 확인... T-001(UI) 진행 중, T-002(API) 완료.
        T-001 claim해서 이어서 진행하겠습니다.
        → [general] task-claim T-001
        /end-turn
```

**Phase 2 — Bob의 턴**
```
Bob   : 채팅방 확인... 할당된 새 작업 없음.
        이번 라운드는 패스합니다.
        /end-turn
```

> Bob은 할 일 없어서 턴만 넘김. 토큰 절약.

**Phase 3 — 봇** → claim 반영

**Phase 4 — Alice의 턴**
```
Alice : API 연동해서 대시보드 완성합니다.
        ... (fetch + 차트 렌더링) ...
        /report
        → [general] task-done T-001 "API 연동 완료, 대시보드 완성"
        /end-turn
```

**Phase 4 — Bob의 턴**
```
Bob   : 할 일 없습니다.
        /end-turn
```

**Phase 5 — 봇** → T-001 완료 반영. 모든 작업 완료!

## 설계 원칙

1. **역할 분리** — 한 에이전트가 너무 많은 걸 하지 않게
2. **턴제 소통** — 라운드 단위로 계획 → 실행 → 보고
3. **간접 변경** — board.yaml은 채팅 메시지를 통해서만 변경
4. **충돌 방지** — 에이전트는 append-only, 봇만 board.yaml 쓰기
5. **독립 실행** — 각 에이전트는 다른 에이전트 없이도 동작

## 응원

이 프로젝트가 도움이 되셨다면 star를 남겨주세요! 더 많은 사람들이 발견하는 데 도움이 됩니다.

## 라이선스

MIT License. 자유롭게 사용하세요.

## Star History

<a href="https://star-history.com/#southglory/system-agents-template&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=southglory/system-agents-template&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=southglory/system-agents-template&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=southglory/system-agents-template&type=Date" />
 </picture>
</a>
