GPIO-like Rule

정의
- 이름이 `*gpio`로 끝나는 기능 신호는 IO PAD 제어를 외부 포트로 모두 노출합니다.

포트 확장
- `{name}_oen`, `{name}_i`, `{name}_pe_pu`, `{name}_ps_pd`, `{name}_st`, `{name}_ie`, `{name}_ds`, `{name}_c`
- `{sub_mode}.sv`, `{mode}_mux.sv`, `pad_mux.sv`에 동일 규칙을 적용합니다.

동작
- `{sub_mode}.sv`에서는 GPIO-like 이름일 경우, 일반 기능 신호 배선 대신 위 제어 포트셋에 `test_io[*]`를 직접 연결합니다.
- test_en과 관계없이 출력 경로는 직결(`test_io[*].I = {name}_i[...]`). OEN은 극성에 따라 지정.

