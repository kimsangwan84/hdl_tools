from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PadRow:
    row: int
    group: str
    name: str
    pad_type: str
    kind: str  # 'I' or 'IO'
    excluded: bool = False
    index: int = -1


@dataclass
class SigCell:
    base: str
    base_idx: Optional[int]
    enable: Optional[str]
    enable_idx: Optional[int]
    marker: str  # 'C' | 'R' | 'none'
    direction: str  # 'I'|'O'|'IO'
    default_in: str
    pad_kind: str  # 'I'|'IO'
    pad_index: int
    pin_name: str
    excel_row: int
    nt_order: Optional[int] = None


@dataclass
class SubMode:
    mode: str
    name: str
    om_values: List[int]
    cells: List[SigCell] = field(default_factory=list)
    index: int = -1


@dataclass
class ExcelModel:
    pads_I: List[PadRow]
    pads_IO: List[PadRow]
    pads_OSC: List[str]
    modes: Dict[str, List[SubMode]]

