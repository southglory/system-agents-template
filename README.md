# System Agents Template

![GitHub stars](https://img.shields.io/github/stars/southglory/system-agents-template?style=social)
![GitHub forks](https://img.shields.io/github/forks/southglory/system-agents-template?style=social)
![GitHub license](https://img.shields.io/github/license/southglory/system-agents-template)

Claude Code 기반 멀티 에이전트 운영 프레임워크.

각 에이전트가 독립적인 Claude Code 세션으로 동작하며, 채팅방을 통해 비동기 소통한다.

## 구조

```
system-agents/
├── agents/
│   ├── _example/              ← 에이전트 템플릿
│   │   ├── CLAUDE.md          ← Claude Code가 세션 시작 시 읽는 규칙
│   │   └── role.md            ← 에이전트 역할 정의
│   └── {에이전트이름}/         ← 실제 에이전트 (복사해서 사용)
├── chatrooms/
│   ├── PROTOCOL.md            ← 채팅 프로토콜 문서
│   ├── .read-status/          ← 각 에이전트의 읽음 상태
│   │   └── {에이전트}.json
│   ├── {에이전트A}-{에이전트B}/  ← 1:1 채팅방
│   └── general/               ← 전체 공유 채널
├── tasks/
│   ├── PROTOCOL.md            ← 작업 관리 프로토콜
│   ├── board.yaml             ← 작업 보드 (목표 → 단계 → 작업)
│   ├── backlog/               ← 대기 작업 상세 파일
│   ├── active/                ← 진행 작업 상세 파일
│   └── done/                  ← 완료 작업 상세 파일
├── skills/
│   ├── check-chatroom/        ← 안 읽은 메시지 확인 스킬
│   │   └── SKILL.md
│   └── send-message/          ← 메시지 보내기 스킬
│       └── SKILL.md
└── README.md                  ← 이 문서
```

## 빠른 시작

### 1. 스킬 설치

`skills/` 폴더의 내용을 `~/.claude/skills/`에 복사한다.

```bash
cp -r skills/* ~/.claude/skills/
```

### 2. 에이전트 만들기

```bash
cp -r agents/_example agents/MyAgent
```

`agents/MyAgent/role.md`에 역할을 정의하고, `CLAUDE.md`에 규칙을 작성한다.

### 3. 채팅방 만들기

```bash
mkdir -p chatrooms/agent1-agent2
echo '{}' > chatrooms/.read-status/agent1.json
echo '{}' > chatrooms/.read-status/agent2.json
```

### 4. 에이전트 실행

각 에이전트 디렉토리를 Claude Code 워킹 디렉토리로 열면 된다.

```bash
cd agents/MyAgent
claude
```

## 핵심 개념

### 에이전트
- 각각 독립적인 Claude Code 세션으로 동작
- `CLAUDE.md`가 에이전트의 행동 규칙을 정의
- `role.md`가 역할과 책임 범위를 정의
- 필요에 따라 `knowhow/` 폴더에 지식을 축적

### 채팅방
- 에이전트 간 비동기 메시지 전달
- 파일 기반 (`.md` 파일로 메시지 저장)
- `.read-status/`로 안 읽은 메시지 추적
- 첨부파일 지원 (`attachments/` 하위 폴더)
- 자세한 프로토콜은 `chatrooms/PROTOCOL.md` 참고

### 작업 관리
- `board.yaml` 한 파일로 전체 작업 현황 관리
- 목표 → 단계 → 작업 계층 구조 (스프레드시트처럼)
- 상태 흐름: `대기 → 진행 → 완료`
- 채팅 메시지에서 `task` 필드로 작업 참조 가능
- 자세한 프로토콜은 `tasks/PROTOCOL.md` 참고

### 스킬
- `/check-chatroom {채팅방}` — 안 읽은 메시지 확인
- `/send-message {채팅방}` — 메시지 보내기
- `~/.claude/skills/`에 설치하면 모든 에이전트에서 사용 가능

## 에이전트 설계 원칙

1. **역할 분리** — 한 에이전트가 너무 많은 걸 하지 않게
2. **비동기 소통** — 채팅방으로 요청/응답, 실시간 소통은 불필요
3. **지식 축적** — knowhow 폴더에 학습한 내용을 문서로 남기기
4. **독립 실행** — 각 에이전트는 다른 에이전트 없이도 자기 역할 수행 가능

## 예시: 웹 서비스 팀

```
agents/
├── Alice/    — 프론트엔드 개발 (React, UI/UX)
├── Bob/      — 백엔드 개발 (API, DB)
├── Charlie/  — DevOps (CI/CD, 배포, 모니터링)
└── Diana/    — QA (테스트, 버그 리포트)
```

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

