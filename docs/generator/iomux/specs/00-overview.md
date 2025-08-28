Overview

목적
- Excel에 정의된 PAD/모드 정보를 바탕으로 Normal/Scan/IPDT 3개 모드의 MUX 로직과 PAD 연결 RTL(SystemVerilog)을 자동 생성합니다.
- 산출물: `pad_mux.sv`, 각 모드별 `{mode}_mux.sv`(`normal_mux.sv`, `scan_mux.sv`, `ipdt_mux.sv`), 각 서브모드 `{sub_mode}.sv`, smoke `testbench.sv`.

플로우
- Excel 로딩 → 시트 구조/헤더 탐지 → 데이터 파싱 → 모델(ExcelModel) 구성 → 스펙 검증(OM/버스/네이밍 등) → RTL/TB 생성 → 선택적으로 zip 패키징.

입력
- Excel 워크북(.xlsx): 시트명 고정 불필요. 상단 3행(모드/서브모드/OM) 머지 구조 전제.
- CLI 옵션: `-i`, `-o`, `--sheet(선택)`, `-pad_type <PAD_CELL> <DIR>`, `-mux_exclude <핀>`, `--zip(선택)`.

출력
- `out/design/pad_mux.sv`
- `out/design/{mode}/{mode}_mux.sv`
- `out/design/{mode}/{sub_mode}.sv`(특수 `io_test`는 생성하지 않음)
- `out/verification/testbench.sv`

아키텍처(모듈 분리 계획)
- excel: 로딩/머지 반영/헤더 탐색/OM 파싱/스팬 검출/모델 구성
- validate: 스펙 검증(B101~B103, C402, C403, O301~O304, U902, U903, S701, P203, F10x)
- codegen: submode/mode_mux/pad_mux/testbench + 공통 헬퍼/정렬
- utils/banner/errors/models: 공용 유틸/버전/예외/데이터 모델

실행(모듈 엔트리)
- `python -m generator.iomux -i <xlsx> -o <out> -pad_type PDIDWUWSWCDG I -pad_type PDDWUWSWCDG IO -mux_exclude OM ...`

DoD(Definition of Done)
- Excel 사양을 문제 없이 파싱/검증하고, 생성된 RTL/TB가 포맷 규칙에 부합하며, 에러 시 적절한 EID로 종료.

