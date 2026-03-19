# {에이전트이름} — {한줄 설명}

## 역할
- 역할 1
- 역할 2

## 턴제 운영

이 시스템은 턴제로 운영된다. 세션이 시작되면 사용자가 현재 Phase를 알려준다.

### Phase 2 (계획) — 이번 라운드에서 할 일 정하기

1. **메시지 읽기**: `/check-chatroom general`로 안 읽은 메시지 확인
2. **보드 확인**: `tasks/board.yaml`을 읽어서 현재 작업 현황 파악 (읽기만)
3. **사용자 보고**: 안 읽은 메시지 요약 + 담당 작업 목록 (우선순위순)
4. **작업 선점**: 수행할 작업이 있으면 `/send-message general`로 `task-claim` 메시지 전송
5. **작업 요청**: 새 작업이 필요하면 `/send-message general`로 `task-create` 메시지 전송
6. **실제 작업은 하지 않는다** — 코드 작성, 파일 수정 등은 Phase 4에서
7. **턴 종료**: `/end-turn`으로 턴을 종료한다

### Phase 4 (실행) — 실제 작업 수행

1. **메시지 읽기**: `/check-chatroom general`로 Phase 3 봇 메시지 확인
2. **보드 확인**: `tasks/board.yaml`에서 자기 담당 작업 확인
3. **작업 수행**: 담당 작업을 실제로 수행
4. **결과 공유**: `/send-message general`로 결과 보고
   - 완료 시: `task-done`
   - 진행 중: `task-update`
   - 일반 공유: `message`
5. **사용자 보고**: 수행 결과를 사용자에게 보고
6. **턴 종료**: `/end-turn`으로 턴을 종료한다

### Phase 알 수 없을 때

사용자가 Phase를 명시하지 않으면:
1. 채팅방 메시지 확인 후 사용자에게 보고
2. board.yaml에서 자기 담당 작업을 사용자에게 보고
3. 사용자의 지시에 따라 행동

## 금지 사항

- **board.yaml을 직접 수정하지 않는다** — 작업 변경은 반드시 채팅 메시지(task-* type)로
- **채팅방 메시지는 반드시 `/send-message`로만 작성** — 직접 파일 생성 금지
- Phase 2에서 코드나 파일을 수정하지 않는다
- Phase 4에서 task-claim을 보내지 않는다

## 채팅방 프로토콜
- 채팅방 위치: `../../chatrooms/`
- 프로토콜 문서: `../../chatrooms/PROTOCOL.md`
- 메시지 보내기: `/send-message {채팅방이름}`
- 메시지 확인: `/check-chatroom {채팅방이름}`

## 작업 관리
- 작업 보드: `../../tasks/board.yaml` (읽기 전용)
- 프로토콜 문서: `../../tasks/PROTOCOL.md`

## 참고 문서
- 역할 정의: `role.md`
