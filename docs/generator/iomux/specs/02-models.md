Models

PadRow
- 필드: `row:int, group:str, name:str, pad_type:str, kind:str('I'|'IO'), excluded:bool, index:int`
- 의미: Excel 한 행의 PAD 정의. excluded면 MUX에서 제외되고 index=-1.

SigCell
- 필드: `base:str, base_idx:Optional[int], enable:Optional[str], enable_idx:Optional[int], marker:str('C'|'R'|'none'), direction:str('I'|'O'|'IO'), default_in:str, pad_kind:str('I'|'IO'), pad_index:int, pin_name:str, excel_row:int, nt_order:Optional[int]`
- 의미: 특정 서브모드 블록 안의 한 신호 라인과 제어 컬럼(마커/방향/기본값), enable 네이밍 짝 등.

SubMode
- 필드: `mode:str('normal'|'scan'|'ipdt'), name:str, om_values:List[int], cells:List[SigCell], index:int`
- 의미: 하나의 서브모드 정의. `index`는 해당 모드의 enable 비트 위치.

ExcelModel
- 필드: `pads_I:List[PadRow], pads_IO:List[PadRow], pads_OSC:List[str], modes:Dict[str,List[SubMode]]`
- 의미: Excel 파싱 결과의 전체 모델.

불변식(요약)
- Pin Name은 모델 내 유일(F103 방지).
- `FORBIDDEN_BASES={OM,PORn,XIN,XOUT}`는 셀에 값이 있으면 오류(P203).
- enable 네이밍은 `<base>_oe`(AH) 또는 `<base>_oen/_oe_n/_oen_n`(AL)만 허용(C403), 베이스 일치(C402).
- 버스 인덱스는 모드별/전역으로 0..W-1 연속(B101), 스칼라/인덱스 혼용 금지(B102), 동일 서브모드 중복 금지(B103).
- 동일 base는 입력/출력 혼용 금지(U902). 서브모드 간 폭 불일치 금지(U903).

