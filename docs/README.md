Generator Documentation

개요
- `generator` 패키지는 여러 생성 도구 모듈을 포함할 수 있습니다. 현재는 `iomux` 모듈이 포함되어 있으며, 추후 `empty_module` 등 추가 모듈을 확장할 수 있습니다.

모듈 별 문서 인덱스
- `docs/generator/iomux/` — IO Mux Generator 문서와 스펙
- `docs/generator/empty_module/` — (향후 추가 예정) 예비 모듈 문서 위치

빠른 시작(iomux)
- 실행: `python -m generator.iomux -i <xlsx> -o <out> ...`
- 예시: `python -m generator.iomux -i generator/iomux/Kameleon_operation_mode_and_test_multiplexing.xlsx -o out_iomux -pad_type PDIDWUWSWCDG I -pad_type PDDWUWSWCDG IO -mux_exclude OM -mux_exclude XIN -mux_exclude XOUT -mux_exclude PORn`

바로가기(iomux 세부 스펙)
- `docs/generator/iomux/specs/00-overview.md`
- `docs/generator/iomux/specs/01-errors.md`
- `docs/generator/iomux/specs/02-models.md`
- `docs/generator/iomux/specs/10-excel.md`
- `docs/generator/iomux/specs/20-validate.md`
- `docs/generator/iomux/specs/30-codegen-common.md`
- `docs/generator/iomux/specs/31-submode.md`
- `docs/generator/iomux/specs/32-mode-mux.md`
- `docs/generator/iomux/specs/33-pad-mux.md`
- `docs/generator/iomux/specs/34-testbench.md`
- `docs/generator/iomux/specs/40-cli.md`
- `docs/generator/iomux/specs/50-formatting.md`
- `docs/generator/iomux/specs/60-io-test.md`
- `docs/generator/iomux/specs/61-nand-tree.md`
- `docs/generator/iomux/specs/62-gpio-like.md`
- `docs/generator/iomux/specs/70-version-stamp.md`
