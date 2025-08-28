Smoke Testbench

개요
- 생성된 `pad_mux.sv`에 대한 가벼운 동작 검증용 TB를 자동 생성합니다.

포트/배선
- 모드 enable 레지스터 선언 및 DUT 연결.
- 기능 신호: 입력은 reg, 출력은 wire로 선언.
- PAD 핀: IN은 logic, IO는 Z 드라이버(`tb_*_oe`/`tb_*_drv`)로 양방향 구동.
- io_test 존재 시: pad_mux에 io_test 포트가 노출되나, 이 TB에서는 의도적으로 미연결(주석 포함).

공통 task
- `disable_all_modes()` — 모든 enable을 0으로.

검증 시퀀스
1) All disable: 입력 기능 신호는 Default 값, PAD 출력 드라이브는 0인지 확인.
2) 단일 sub_mode 활성화 루프: 모드별/서브모드별로 enable 한 비트만 1로 설정 후
   - 출력 경로: 기능 입력 토글 → PAD `.I` 토글 관찰
   - 입력 경로: PAD 핀 토글 → 기능 신호 토글 관찰
   - 기타 신호 불변성 체크

판정/로그
- `$error`가 하나라도 발생하면 FAIL.
- 메시지 포맷: `[TB] <kind> | mode=<m> sub_mode=<name> base=<b> idx=<i> exp=<e> got=<g>`

한계
- 조합 로직 중심의 스모크 수준 검증. 타이밍/메타스테이블리티/아날로그 행태는 다루지 않습니다.

