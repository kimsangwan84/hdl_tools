Sub-mode Module `{sub_mode}.sv`

Ports
- `input  logic         test_en`
- `if_pad_in.core       test_in  [0:NI-1]`
- `if_pad_io.core       test_io  [0:NO-1]`
- 기능 신호들: 엑셀 1열의 신호명(버스 폭 자동 인지)
- GPIO-like 확장: 이름이 `*gpio`로 끝나면 `{name}_oen/_i/_pe_pu/_ps_pd/_st/_ie/_ds/_c`

Body
- 입력 경로: 입력(I/IO-as-input)
  - `assign <signal> = test_en ? test_in/io[idx].C : <default>;`
  - 입력 경로의 TI_* 고정값 구동(TI_PE_PU/PS_PD/ST/IE/I/OEN/DS)
- 출력 경로: 출력(O/IO-as-output)
  - `assign test_io[idx].I = <signal>;` (test_en 게이트 없음)
  - 출력 경로의 TO_* 고정값 구동(TO_PE_PU/PS_PD/ST/IE/DS, OEN은 enable 극성 반영)

특수: nand_tree
- 포트는 `test_en/test_in/test_io`만.
- 입력 후보: 서브모드에 입력으로 사용된 모든 IN/IO PAD의 `.C`.
- 입력 순서: `nt_in[n]`(혹은 `nand_tree_in[n]`) 표기가 있으면 n 순서, 없으면 엑셀 행 순서.
- 구현: `primemas_lib_nand2` 체인으로 연쇄, 최종 출력을 모든 IO PAD의 `.I`에 연결.

특수: io_test
- 별도 `{sub_mode}.sv`는 생성하지 않음. mode_mux/pad_mux에서 패스스루 포트 제공.

제약/검증
- 동일 base 입력/출력 혼용 금지(U902). 서브모드 간 폭 불일치 금지(U903).
- GPIO-like는 기능 신호 대신 제어 포트셋으로 대체 연결.

