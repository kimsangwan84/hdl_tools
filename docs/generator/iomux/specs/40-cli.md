CLI

실행
- 모듈 엔트리: `python -m generator.iomux [OPTIONS]`

옵션
- `-i, --input <xlsx>`: Excel 파일 경로(필수)
- `-o, --outdir <dir>`: 출력 디렉터리(필수)
- `--sheet <name>`: 시트 이름(선택, 미지정 시 자동 탐색)
- `-pad_type <PAD_CELL> <DIR>`: 공정별 PAD 셀과 방향(I/IO). 여러 번 지정 가능(필수).
- `-mux_exclude <핀>`: 제외할 핀(베이스만 지정해도 멀티비트 전체). 여러 번 지정 가능.
- `--zip <path.zip>`: 출력 디렉터리를 zip으로 패키징(선택)

예시
```
python -m generator.iomux \
  -i generator/iomux/Kameleon_operation_mode_and_test_multiplexing.xlsx \
  -o out_iomux \
  -pad_type PDIDWUWSWCDG I \
  -pad_type PDXOEDG16RFRD IO \
  -pad_type PDDWUWSWCDG IO \
  -pad_type PDDWUWSWCDGS IO \
  -mux_exclude OM -mux_exclude XIN -mux_exclude XOUT -mux_exclude PORn
```

오류/종료 코드
- openpyxl 미설치/로드 실패(U901), 스펙 위반(Fxxx/Pxxx/Oxxx/Cxxx/Sxxx/Uxxx) 시 3으로 종료.

