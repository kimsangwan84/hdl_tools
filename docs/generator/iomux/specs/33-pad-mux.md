Top `pad_mux.sv`

Ports
- `normal_mode_enable[31:0]`, `scan_mode_enable[15:0]`, `ipdt_mode_enable[15:0]`
- 모든 모드의 기능 신호(주석 블록으로 모드/공유/전용 구분)
- 모든 PAD 핀: IN(`input`), IO(`inout`) — 벡터 가능
- OSC: `XIN`(input), `XOUT`(output)
- io_test 존재 시 top-level에도 `io_test_osc_io`, `io_test_in`, `io_test_io` 노출

Body
- normal/scan/ipdt의 `{mode}_mux`를 인스턴스화.
- PAD 인터페이스 신호를 모드별 결과로 OR/선택하여 구동. test_on=|scan or |ipdt 기준으로 normal과 구분.
- C 경로(anchor)를 위해 모든 PAD C 입력에 `primemas_lib_buf` 삽입.
- OSC PAD는 `primemas_lib_OSC_PAD` 인스턴스 사용, `REF/RD=2'b11` 고정, `XC` 경로에 버퍼 삽입.
- PAD 인스턴스 명은 `_NNN` 0패딩 관례 사용.

제약/검증
- 금지 핀에 대한 MUX 정의 금지(P203). 제외된 핀은 포트에는 존재하되 내부 MUX 계산에서 빠짐.

