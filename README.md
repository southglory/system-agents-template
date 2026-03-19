# System Agents Template

![GitHub stars](https://img.shields.io/github/stars/southglory/system-agents-template?style=social)
![GitHub forks](https://img.shields.io/github/forks/southglory/system-agents-template?style=social)
![GitHub license](https://img.shields.io/github/license/southglory/system-agents-template)

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
│   └── end-turn/              ← 턴 종료
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

# Phase 2: 각 에이전트 계획
cd agents/AgentA && claude    # "Phase 2" 알려주기
cd agents/AgentB && claude

# Phase 3: 봇
python bot/turn-bot.py

# Phase 4: 각 에이전트 실행
cd agents/AgentA && claude    # "Phase 4" 알려주기
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

## 설계 원칙

1. **역할 분리** — 한 에이전트가 너무 많은 걸 하지 않게
2. **턴제 소통** — 라운드 단위로 계획 → 실행 → 보고
3. **간접 변경** — board.yaml은 채팅 메시지를 통해서만 변경
4. **충돌 방지** — 에이전트는 append-only, 봇만 board.yaml 쓰기
5. **독립 실행** — 각 에이전트는 다른 에이전트 없이도 동작

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
