---
description: [Antigravity] 프로젝트 정수 추출(Ark) 초기화
---
이 워크플로우는 새 프로젝트를 맡은 Antigravity 에이전트가 시스템 에이전트 프레임워크를 기반으로 프로젝트 분석을 시작할 때 사용합니다.

// turbo
1. 시스템 에이전트 구조 확인
   - `.system-agents/tasks/board.yaml`을 읽어 현재 작업과 진행 상황을 파악합니다.

// turbo
2. 채팅방 맥락 파악
   - `.system-agents/chatrooms/general/`의 최신 메시지를 읽어 이전 에이전트의 작업 결과를 확인합니다.

// turbo
3. Antigravity 역할 활성화
   - `.system-agents/agents/antigravity/role.md`에 정의된 원칙에 따라 분석 모드로 진입합니다.

4. 소프트웨어 정수(Essence) 추출 시작
   - 프로젝트의 핵심 로직을 탐색하고 `analysis/` 폴더에 문서화를 시작합니다.
