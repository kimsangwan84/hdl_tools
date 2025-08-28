Codegen Common

버스 맵
- per-mode: `build_bus_maps_for_mode(subs)` → (sig_w, sig_dir, en_w, per_sub)
  - sig_w[base]=폭(W), sig_dir[input|output], en_w[<base>_oe*]=폭
- global: `build_bus_maps_global(modes)` → top 정형 포트 폭 결정.

포트/선언/연결 정렬 규칙 요약
- 포트 선언 순서: `${DIRECTION} ${TYPE} ${BITS} ${NAME} ${ARRAY}`.
- 인터페이스(`if_pad_* .core`)는 DIR+TYPE 열보다 넓게 잡아 같은 칼럼 정렬.
- 인덱스/폭 표기(`[MSB:LSB]`)는 우정렬.
- 인스턴스 포트 연결은 세로 정렬, 행 단위 분리.
- 이름 패딩: 인스턴스 bit 라벨은 `_NNN`처럼 0패딩(3자리 기본).

선택/결합 규칙
- submode → mode_mux: enable 비트로 각 서브모드 출력들을 OR-combine. io_test는 패스스루 소스로 포함.
- mode_mux → pad_mux: normal/scan/ipdt 3모드 중 scan/ipdt가 우선하여 test_on일 때 해당 모드 선택, 아니면 normal.
- C 경로(anchor): 모든 sub_mode/mode_mux에서 C 신호 경로에 `primemas_lib_buf` 버퍼를 삽입.

OSC PAD
- `primemas_lib_OSC_PAD` 인스턴스 사용, `REF/RD=2'b11` 고정, `XC`에 버퍼 삽입.

