io_test Passthrough

정의
- Excel에서 `io_test`(대소문자 무시, 공백/하이픈 허용)의 서브모드가 존재하면, 해당 서브모드는 별도 `{sub_mode}.sv`를 생성하지 않고 패스스루 포트를 노출합니다.

포트
- mode_mux: `io_test_osc_io`, `io_test_in`, `io_test_io`
- pad_mux: 동일 포트를 top-level에도 노출하여 외부에서 테스트용으로 직접 구동 가능

선택 로직
- 해당 모드의 enable 비트가 `io_test` 위치에 설정되면, `test_in/io` 값은 io_test 포트에서 직접 들어옵니다.

테스트벤치
- smoke TB에서는 io_test 포트를 의도적으로 미연결로 둡니다(간단 시나리오 유지).

