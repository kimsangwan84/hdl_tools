Mode MUX `{mode}_mux.sv`

Ports
- `{mode}_mode_enable[W-1:0]`
- `if_pad_in.core  test_in [0:NI-1]`
- `if_pad_io.core  test_io [0:NO-1]`
- 기능 신호(서브모드 간 공유는 1회 선언, enable 기반 OR-선택)
- GPIO-like 확장 동일 적용
- io_test 특수 포트(존재할 때): `io_test_osc_io`, `io_test_in`, `io_test_io`

Body
- 각 서브모드를 인스턴스화하여 `test_in/io`를 전달하고, `test_en`은 해당 enable 비트에 연결.
- 중복 신호는 내부 wire로 수집 후 enable로 OR-선택.
- `C` 경로는 `primemas_lib_buf` anchor buffer 삽입.
- io_test가 있으면 해당 enable 비트 시 `io_test_*` 포트가 선택 경로의 소스가 됨.

제약/검증
- 동일 신호의 서브모드 간 폭 불일치 시 U903.

