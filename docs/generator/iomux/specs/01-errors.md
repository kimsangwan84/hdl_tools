Errors (EID)

정책
- 모든 에러는 고유 코드(EID)와 함께 즉시 종료합니다. 메시지는 맥락 정보를 포함합니다.

목록
- B101: 버스 인덱스 불연속 — 사용된 인덱스가 0..W-1 연속이 아님
- B102: 버스 스칼라/인덱스 혼용 — 동일 base에서 스칼라와 인덱스 표기를 함께 사용
- B103: 버스 인덱스 중복 정의(동일 서브모드)
- F101: 엑셀 병합 포맷 오류(필수 머지/헤더 누락)
- F102: 모드/서브모드/OM 헤더 탐지 실패
- F103: Pin Name 중복
- F104: mode/sub_mode 블록 시작 또는 내부에 빈 셀 존재 (STRICT)
- F105: mode/sub_mode 병합 불연속 — 중간에 비머지/빈 셀/공백 행·열 존재 (STRICT)
- F106: §3.2 위반 — 우측 3열 배치/값 오류(잘못된 값, 위치 불일치, 빈 칸인데 다른 열에 기입됨)
- P201: `-pad_type` 미지정
- P202: I-only PAD에 O/IO 지정
- P203: 금지 핀(OM/XIN/XOUT/PORn)에 MUX 정의됨
- O301: OM 값 범위 초과
- O302: OM 값 중복(서브모드 간)
- O304: 동일 서브모드에서 OM 정의 충돌
- C402: enable 베이스 불일치 — `signal / enable` 쌍에서 enable 이름 베이스가 다름
- C403: OE 네이밍 규칙 위반(`oe`/`oen`/`oe_n`/`oen_n`)
- S701: `-mux_exclude`인데 엑셀에 정의 존재
- U901: Unexpected error (비정상 예외)
- U902: 동일 base에 입력/출력 혼용
- U903: 동일 신호가 서브모드 간 버스폭 불일치

메시지 포맷
- `[<EID>] <설명> | key=value ...`

예시
- `[F106] §3.2 control columns violation (order/value/placement) | row=42 submode=normal_gpio col=17 field=direction value=""`
- `[C403] OE must be '<signal>_oe' ... | signal=TDO enable=TDI_oen submode=scan_jtag`

