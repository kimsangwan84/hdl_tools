# IO Mux Generator (Excel → SystemVerilog)
*Last updated: 2025-08-27 KST*

## 1) 목적
엑셀에 정의된 PAD/모드 정보를 바탕으로 **Normal / Scan / IPDT** 3개 모드의 MUX 로직과 PAD 연결을 자동 생성한다. 산출물은:
- `pad_mux.sv`
- 각 모드별 `{mode}_mux.sv` (`normal_mux.sv`, `scan_mux.sv`, `ipdt_mux.sv`)
- 각 서브 모드별 `{sub_mode}.sv`

---

## 2) 입력

### 2.1 Excel 워크북
- `-i <엑셀 파일 경로>`
- Excel 파일에 여러 시트가 있어도 자동으로 **파싱 가능한 시트**를 탐색한다. (고정 시트명 불필요)
- 상단 **3행 머지 구조**를 전제로 시작 위치를 찾는다.
  1) `Pin Group`
  2) `Pin Name`
  3) `PAD type`
- 셀 텍스트의 **대소문자 무시**, 철자만 일치하면 됨.
- `Pin Name`은 **유일**해야 한다.

### 2.2 PAD type 매핑
- 공정 별 실제 PAD 셀 타입을 CLI에서 제공:
  ```bash
  -pad_type {PAD_CELL_NAME} {DIR}   # DIR ∈ {I, IO}
  # 예) -pad_type PDIDWUWSWCDG I  -pad_type PDDWUWSWCDG IO
  ```
- 엑셀 `PAD type` 표기에 붙을 수 있는 **`_V` / `_H`**(macro 방향)는 **매칭에서 제외**하고, 실제 인스턴스 생성 시 **ORIENTATION 파라미터**로만 사용한다.

### 2.3 MUX 제외
- `-mux_exclude <핀 이름>` 옵션은 여러 번 사용 가능.  
  예) `-mux_exclude OM -mux_exclude XIN -mux_exclude XOUT -mux_exclude PORn`
- **이름만** 지정해도 멀티비트 전부 제외된다(예: `OM[5]` 등 전체).
- 제외한 핀은 NI/NO 산정에서 빠진다.
- 제외했는데 엑셀에 매핑이 있으면 **에러 종료(S701)**.

---

## 3) Excel 레이아웃 (서브모드 테이블)

### 3.1 수평 머지 구조(3개 행)
- 1행: 모드 구분 → `Normal / Scan / IPDT`
- 2행: 서브 모드 이름(`sub_mode`)
- 3행: **OM 값 목록** — `,`로 다중, `~`로 범위, 10진/16진(`0x..`/`8'h..`) 혼용 허용
- 한 서브모드는 OM 값을 **여러 개** 가질 수 있다.
- 서로 다른 서브모드가 같은 OM을 갖거나, 범위를 벗어나면 에러.
- **명시되지 않은 OM 값은 reserved**(= 모든 서브모드 비활성 처리).
- 서브모드 이름에 "reserved"(대소문자 무시)가 포함된 열은 **생성에서 제외**한다.

### 3.2 각 서브모드 열(최소 4개: 좌측 1, 우측 3 = Marker / Direction / Default)
열 구성(좌→우, STRICT):
1) **Signal name (왼쪽 첫 열)** — 비어 있으면 스킵. `sig[n]`처럼 비트 선택이 있으면 최종 포트는 **멀티비트**로 승격(`sig[2:0]` 등).
2) **Marker (블록의 마지막-2 열)** — `C`(Clock) / `R`(Reset). (값 외 입력은 오류(F106). 버퍼 정책은 §7.2 따름)
3) **Direction (블록의 마지막-1 열)** — `I` / `O` / `IO` **(공란 불가)**. I-only PAD에 O/IO 지정 시 에러. **해당 값 외는 오류(F106)**.
4) **Default (블록의 마지막 열)** — *입력 경로* 디폴트 값. 공란이면 `1'b0`. 허용 값은 `0 / 1 / 1'b0 / 1'b1` 만 (그 외는 오류).

규칙:
- **Enable 동반 표기**: `signal / enable` 형식 허용.  
  Enable 네이밍은 **postfix 규칙**만 허용:
  - Active-high: ` _oe`
  - Active-low:  ` _oen`, ` _oe_n`, ` _oen_n`
  (예: `TDO / TDO_oen` → `.C`에 `TDO`, `.OEN`에 `TDO_oen` 연결)
- 각 서브모드 블록은 **최소 4열**이며, **우측 3열은 항상** `Marker / Direction / Default` 순서를 따른다.
- 중간에 부가 열(메모/주석 등)이 있어도 무방하나, 파서는 이를 **무시**한다. 단, 우측 3열이 비어 있는데 다른 열에 해당 값이 기입된 경우는 **오류(F106)**.

**버스 인덱스 규칙 (멀티비트)**
- 같은 base 이름으로 `sig[0]`, `sig[1]`, … 처럼 **인덱스 표기를 사용하면**, 생성 결과는 멀티비트 버스가 된다.
- 이때, 각 모드(mode) 단위 및 전체(top) 단위로 다음을 **엄격하게** 검사한다.
  1) **연속성(B101)**: 사용된 인덱스 집합이 `0..W-1`로 **연속**이어야 한다(예: `[0,1,3]` → 오류).
  2) **스칼라/인덱스 혼용 금지(B102)**: `sig`(스칼라)와 `sig[2]` 같은 **혼용**은 금지.
  3) **중복 정의(B103)**: 동일 서브모드 안에서 같은 인덱스를 **중복 표기**하면 오류(예: 한 서브모드 내에 `sig[1]` 두 행).

### 3.3 모드/서브모드 머지 및 연속성 규칙
- Excel 시트에서 **mode**, **sub_mode** 영역은 새로운 블록이 시작될 때 **빈 셀을 허용하지 않는다**. 각 블록의 시작 행부터 끝 행까지 값이 **연속적으로 존재**해야 한다.
- 각 모드/서브모드 블록은 반드시 **머지된 셀로 연속**되어야 하며, 중간에 **비머지 셀**이나 **빈 셀**이 끼어 있으면 **포맷 오류**로 간주한다.
- 다른 모드로 전환될 때에도, 이전 블록의 머지 범위가 끝나는 즉시 다음 블록의 머지 범위가 **바로 이어져야** 하며, 사이에 공백 행/열이나 빈 셀을 두면 안 된다.
- 위 규칙 위반 시 즉시 종료한다 (F104/F105).

---

## 4) OM → 모드 enable 매핑
- OM이 6비트라면 값 범위는 0~63(=64개). 범위를 벗어나면 에러.
- 매핑:
  - `normal_mode_enable[31:0]`  ← OM 0~31
  - `scan_mode_enable[15:0]`    ← OM 32~47
  - `ipdt_mode_enable[15:0]`    ← OM 48~63
- 각 비트는 **active-high**. OM 충돌 금지.

---

## 5) 금지/특수 핀
- **절대 MUX 금지**: `OM`, `XIN`, `XOUT`, `PORn` (필요 시 `-mux_exclude`로도 제외)
- OSC(XIN/XOUT)은 **OSC PAD**로 직접 연결.

---

## 6) 산출물 구조
```
out/
  design/
    pad_mux.sv
    normal/
      normal_mux.sv
      <sub_mode>.sv ...
    scan/
      scan_mux.sv
      <sub_mode>.sv ...
    ipdt/
      ipdt_mux.sv
      <sub_mode>.sv ...
  verification/
    testbench.sv
```

## 7) 검증(Verification) – 자동 생성 testbench.sv

### 7.1 개요
- 생성기는 기본 검증용 **`verification/testbench.sv`**를 함께 생성한다.
- 목적: 스펙의 연결 규칙/디폴트/enable 동작을 **Self-checking**으로 빠르게 검증.
- DUT는 `design/pad_mux.sv` 단일 모듈을 인스턴스한다.

### 7.2 테스트벤치 공통
- `timescale 1ns/1ps` 고정, 클록/리셋 없음(모두 조합 경로 검증 중심).
- 모든 PAD 포트(입력/IO)는 TB 내부의 **wires/reg**로 연결하여 구동/모니터한다.
- 각 모드별 enable 포트: `normal_mode_enable[31:0]`, `scan_mode_enable[15:0]`, `ipdt_mode_enable[15:0]`를 TB가 직접 구동한다.
- 기능 신호 포트(각 base 및 enable들)는 TB에서 **reg/wire**로 선언하고 DUT에 연결한다.

### 7.3 TB 내 공통 task (자동 생성)
- `task automatic disable_all_modes();` → 모든 `*_mode_enable`을 0으로 설정.
- `task automatic pulse_output(input string base, input int idx);` → (해당 신호가 **출력**인 경우) 기능 포트 `<base>[idx]`를 `0→1→0`으로 토글.
- `task automatic pulse_pad(input string base, input int idx);` → (해당 신호가 **입력**인 경우) PAD 핀 `<base>[idx]`를 `0→1→0`으로 토글.
- `task automatic expect_stable_others(input string cur_mode, input int cur_bit);` → 현재 enable 중인 서브모드 외의 모드/서브모드 관련 신호/PAD들이 **불변**임을 체크(X/Z 금지 포함).
- `task automatic check_default(input string base, input int idx, input logic exp);` → all disable 시 기능 입력 신호가 **Default** 값을 가지는지 확인.

> 인덱스 없는 스칼라는 `idx=-1`로 약속하고, TB에서는 단일 비트 신호를 직접 참조한다.

### 7.4 검증 시퀀스
1) **All disable 기본값 검증**  
   - `disable_all_modes();`
   - 모든 **입력 방향** 기능 신호에 대해 `check_default(base, idx, default_value)` 수행. 
   - 모든 **PAD 출력 드라이브**(`.I`)는 0이어야 함(모든 enable=0 → OR-선택 결과 0).

2) **단일 sub_mode 활성화 루프**  
   각 모드(`normal`/`scan`/`ipdt`)에 대해, 각 서브모드 비트 `k`를 **하나씩만** set:
   - `disable_all_modes();`
   - 해당 모드의 `*_mode_enable[k] = 1'b1`로 설정.
   - 이 서브모드에 정의된 각 기능 신호에 대해, 단계별 검증(0→1→0) 을 수행한다.
     - **출력(O/IO 출력으로 사용)**: `pulse_output(base, idx)` 수행 → 연결된 PAD의 `.I`가 `0→1→0`으로 토글되는지 확인.
     - **입력(I/IO 입력으로 사용)**: `pulse_pad(base, idx)` 수행 → 기능 신호가 `0→1→0`으로 토글되는지 확인.
   - `expect_stable_others(cur_mode, k)`로 **현 활성 sub_mode 이외**의 신호/PAD가 **변하지 않음**을 확인.

### 7.5 생성 규칙(자동화 세부)
- TB는 엑셀 파싱 결과를 사용해 **신호 방향(I/O/IO)**, **디폴트 값**, **버스 폭**을 자동 인지한다.
- **GPIO-like(`*gpio`)** 포트셋은 TB에서도 동일 이름으로 선언/연결되며, 필요 시 출력/입력 체크에 포함한다. (단, 내부 동작은 상수 TO_/TI_로 고정되어 있어 기능 신호 토글만 검증)
- `io_test` 서브모드가 존재하는 모드의 경우, DUT 포트(`io_test_osc_io`, `io_test_in`, `io_test_io`)는 선언·연결하되, enable 비트 루프에서는 제외한다(패스스루 전용).

### 7.6 패스/Fail 기준
- 위 7.4의 각 체크가 모두 `$error` 없이 통과하면 **PASS**. 하나라도 실패하면 **FAIL**로 종료한다.
- 메시지 포맷: `[TB] <kind> | mode=<m> sub_mode=<name> base=<b> idx=<i> exp=<e> got=<g>`

### 7.7 한계/비고
- 타이밍/메타스테이블리티는 다루지 않는다(조합 논리 검증 위주). 필요 시 별도 CDC/STA 환경에서 검증.
- PAD macro 동작은 **모델 단순화**(논리 연결 가정). 별도 아날로그 동작은 범위 바깥.

---

## 8) 모듈 스펙

### 8.1 `{sub_mode}.sv`
**Ports**
- `input  logic         test_en`
- `if_pad_in.core       test_in [0:NI-1]`
- `if_pad_io.core       test_io [0:NO-1]`
- 엑셀 1열의 **기능 신호들**(PAD 아님)
- **GPIO-like 확장**: **이름이 `*gpio`로 끝나면** 제어 포트를 모두 노출  
  - `{name}_oen`, `{name}_i`, `{name}_pe_pu`, `{name}_ps_pd`, `{name}_st`, `{name}_ie`, `{name}_ds`, `{name}_c`

**Body**
- **입력 경로**: 기능 신호가 입력이면  
  `assign <signal> = test_en ? test_in/io[idx].C : <default>;`  
  IN/IO를 입력으로 쓸 때 TI_*(`PE/PS/ST/IE` …)는 `gpio_pkg` 상수로 고정.
- **IO 출력 경로**: 기능 신호가 출력이면  
  `assign test_io[idx].I = <signal>;` **(test_en으로 게이트하지 않음)**  
  출력 IO의 `PE_PU/PS_PD/ST/IE/DS`는 TO_* 상수, `.OEN`은 enable 극성을 반영(`_oen/_oe_n`은 active-low).
- **중요**: sub_mode 안에서는 **disable 시 IO에 디폴트 드라이브를 넣지 않음**. 최종 게이팅/선택은 `{mode}_mux.sv`가 담당.

**특수 서브모드 — `nand_tree`**
- Excel에서 sub mode로 정의가 되어 있어야 함.
- 포트는 `test_en`, `test_in`, `test_io` **만**.
- 입력 후보는 서브모드 표에서 *입력으로 사용된* 모든 IN/IO PAD의 `.C`.
- 입력 순서: `nand_tree_in[n]`(또는 `nt_in[n]`) 표기가 있으면 **n 순서**, 없으면 **엑셀 행 순서**.
- **NAND 체인 구현**:
  1. 첫 두 입력을 `primemas_lib_nand2`에 연결 (`.A`, `.B` 포트 사용)하여 첫 출력(`nand_out[0]`)을 생성한다.
  2. 이후 입력들은 직전 출력과 현재 입력을 다시 `primemas_lib_nand2`에 연결하여 연쇄적으로 출력한다.  
     예:
     ```verilog
     primemas_lib_nand2 u_nand_000 ( .A(test_in[0].C),     .B(test_in[1].C),     .Y(nand_out[0]) );
     primemas_lib_nand2 u_nand_001 ( .A(nand_out[0]),      .B(test_in[2].C),     .Y(nand_out[1]) );
     primemas_lib_nand2 u_nand_002 ( .A(nand_out[1]),      .B(test_in[3].C),     .Y(nand_out[2]) );
     // ...
     ```
  3. 최종 출력은 모든 출력 IO PAD의 `test_io[*].I`에 연결한다(복수여도 동일 신호). TI_* / TO_* 규칙 준수.

**특수 서브모드 — `io_test`**
- **위치**: `pad_mux.sv` 밖에서 별도로 구현하는 테스트 모드로 `io_test.sv`는 생성하지 않는다.
- Excel에서 sub mode로 정의가 되어 있어야 함.

### 8.2 `{mode}_mux.sv`
**Ports**
- `{mode}_mode_enable[W-1:0]` → 각 `{sub_mode}`의 `test_en`에 연결
- `if_pad_in.core test_in`, `if_pad_io.core test_io`
- **서브모드 간 중복 신호**는 포트 **한 번만** 선언  
  (여러 서브모드에서 같은 이름을 쓰면 내부에서 enable 기반 MUX/OR-선택)
- **서브모드 간 같은 이름의 폭이 다르면 에러**(U903)
- GPIO-like 규칙 동일 적용

- **io_test 특수 포트**:
  - `if_pad_osc.core  io_test_osc_io` : io_test 모드 enable시 외부에서 OSC PAD를 직접 제어하기 위한 port. MUX를 위한 목적이 아닌 XC를 다른 PAD로 연결하기 위함.
  - `if_pad_in.core   io_test_in`     : io_test 모드 enable시 외부에서 입력 PAD들을 제어하기 위한 port
  - `if_pad_io.core   io_test_io`     : io_test 모드 enable시 외부에서 IO PAD들을 제어하기 위한 port
  - 위의 port는 `pad_mux.sv` 외부에서 제어하기 위해, `pad_mux.sv`의 port에도 생성되어 연결이 필요되어야 한다.

**Body**
- 각 서브모드를 인스턴스화하여 `test_in/io`를 전달하고 `test_en`은 해당 enable 비트에 연결.
- 중복 신호는 내부 wire에 `{sub_mode 접두 normal_/scan_/ipdt_ 제거}`를 prefix로 붙여 구분 후, enable로 OR-선택.
- **C 경로는 항상** `test_in/io[*].C` 경로에 **anchor buffer**(`primemas_lib_buf`)를 삽입한다. (Marker=C는 문서적 표식이며 버퍼 삽입 여부와 무관)

### 8.3 `pad_mux.sv`
**Ports**
- `normal_mode_enable[31:0]`, `scan_mode_enable[15:0]`, `ipdt_mode_enable[15:0]`
- 모든 **모드의 기능 신호**(주석으로 블록 구분; enable 포트는 관련 신호 바로 옆에 배치)
- 모든 **PAD 핀**: IN 전용은 `input`, IO는 `inout` (벡터 가능)
- OSC: `XIN`(input), `XOUT`(output)

**Body**
- Normal/Scan/IPDT 모드는 기존과 동일한 선택 로직을 적용한다.
- XIN/XOUT에는 OSC PAD를 사용하며, 아래와 같이 REF/RD 신호를 고정한다.
- `primemas_lib_OSC_PAD`의 `REF`와 `RD` 신호는 pad_mux에서 고정값(`2'b11`)을 할당하며, `primemas_lib_buf`를 사용하여 OSC의 clock 경로(`XC`)에 버퍼를 삽입한다.
- XIN 신호가 clock 역할을 하므로, `pad_osc_io.XC` 연결 시 anchor buffer(`primemas_lib_buf`) 삽입이 필수다.
  ```verilog
  assign pad_osc_ref = 2'b11;
  assign pad_osc_rd  = 2'b11;

  primemas_lib_OSC_PAD #(.ORIENTATION("V")) u_0_000_pad_XIN_XOUT (
      .XIN(XIN),
      .XOUT(XOUT),
      .XE(pad_osc_io.XE),    // PAD enable
      .DS(pad_osc_io.DS),    // drive strength
      .REF(pad_osc_ref),     // 고정값 (2'b11)
      .RD(pad_osc_rd),       // 고정값 (2'b11)
      .XC(pad_osc_io_XC),    // clock in/out (buffer 연결 필요)
      .RTE(1'b0)             // test enable (사용하지 않음)
  );
  // OSC XC 경로에는 버퍼 추가
  primemas_lib_buf u_3_000_exti_XIN_XOUT (
      .A(pad_osc_io_XC),
      .Y(pad_osc_io.XC)
  );
  ```

---

## 9) 포맷/정렬 규칙

### 9.1 포트 선언
- 순서: **`${DIRECTION} ${TYPE} ${BITS} ${SIGNAL_NAME} ${ARRAY}`**
- 각 열은 그 문서 내 **최대 길이 기준**으로 정렬.
- `[MSB:LSB]` 숫자는 **우정렬**(`[ 31:0]`, `[127:0]`).
- 인터페이스(`if_pad_xxx.core`)는 좌측 폭을 일반 `DIR+TYPE`보다 **넓게** 잡아 동일 칼럼에 정렬.
- **주석**은 `DIRECTION` 시작 칼럼에 맞춰 달아 가독성 높임.

### 9.2 if_pad assign
- 필드명(`OEN/IE/C` 등) 폭 3 기준으로 **세로 정렬**.
- 인덱스(`test_in[  9]`)는 **우정렬**.
- `?:` 단문에서도 동일 정렬 규칙 유지.

### 9.3 인스턴스 연결
- 포트명/신호명 칼럼 너비를 계산해 **세로 정렬**.
- 긴 한 줄로 쓰지 않고 **행 단위로 나눠** 연결(가독성).

### 9.4 이름 패딩
- 인스턴스 bit 라벨은 `_NNN`처럼 **고정 0패딩**(최소 3자리, 또는 최대 인덱스 자릿수).

---

## 10) GPIO-like 규칙
- **이름이 `*gpio`로 끝나면** if_pad_io의 모든 제어를 외부 포트로 노출:
  - `{name}_oen`, `{name}_i`, `{name}_pe_pu`, `{name}_ps_pd`, `{name}_st`, `{name}_ie`, `{name}_ds`, `{name}_c`
- 이 규칙은 `{sub_mode}.sv`, `{mode}_mux.sv`, `pad_mux.sv` **모두**에 적용.

---

## 11) 인터페이스 및 패키지 정의

### 11.1 `if_pad_osc`
OSC PAD용 인터페이스는 다음과 같이 정의한다.
```verilog
interface if_pad_osc;
    logic           XE;    // PAD enable (high=enable)
    logic   [3:0]   DS;    // drive strength
    logic           XC;    // clock input/output

  modport pad (
    input           XE,    // PAD 방향에서는 XE, DS 입력
    input           DS,
    output          XC     // PAD에서 코어로 clock 출력
  );

  modport core (
    output          XE,    // 코어에서 PAD로 XE, DS 출력
    output          DS,
    input           XC     // 코어 입력
  );
endinterface : if_pad_osc
```
- `XE`와 `DS`는 PAD를 enable하고 drive strength를 제어하는 신호이며, `XC`는 OSC PAD의 clock 입출력 신호이다.

### 11.2 `if_pad_in`
- 입력 전용 PAD를 위한 interface.
```verilog
interface if_pad_in;
    logic           PE;
    logic           PS;
    logic           ST;
    logic           IE;
    logic           C;

	modport pad (
    input           PE  , 
    input           PS  ,
		input           ST  , 
    input           IE  , 
		output          C
	);

	modport core (
    output          PE  , 
    output          PS  ,
		output          ST  , 
    output          IE  , 
		input           C
	);
endinterface : if_pad_in
```
- **주의**: 출력 관련 포트는 존재하지 않으며, 모든 포트는 TI_* 상수에 의해 고정된다.

### 11.3 `if_pad_io`
- 입출력 PAD를 위한 interface. 입력과 출력 경로를 모두 갖는다.
```verilog
interface if_pad_io;
    logic           OEN;
    logic           I;
	  logic   [ 3:0]  DS;
    logic           PE_PU;
    logic           PS_PD;
    logic           ST;
    logic           IE;
    logic           C;

	modport pad (
    input           OEN   , 
    input           I     , 
    input           DS    ,
    input           PE_PU , 
    input           PS_PD , 
		input           ST    , 
    input           IE    , 
		output          C
	);

	modport core (
    output          OEN   , 
    output          I     , 
    output          DS    ,
    output          PE_PU , 
    output          PS_PD , 
		output          ST    , 
    output          IE    , 
		input           C
	);
endinterface : if_pad_io
```

### 11.4 `gpio_pkg`
- TI_/TO_ 접두사가 붙은 각종 상수 정의 패키지.
- **TI_** : 입력 테스트 모드에서 사용되는 default 값들. 예) `TI_PE_PU`, `TI_PS_PD`, `TI_ST`, `TI_IE`.
- **TO_** : 출력 테스트 모드에서 사용되는 default 값들. 예) `TO_PE_PU`, `TO_PS_PD`, `TO_ST`, `TO_IE`, `TO_DS`.
```verilog
package gpio_pkg;
  localparam    TIE_L       = 1'b0;
  localparam    TIE_H       = 1'b1;

  // GPIO Configuration Case
  localparam    OE_DIS      = 1'b1;
  localparam    OE_ENA      = 1'b0;

  localparam    DS_0        = 4'h0;
  localparam    DS_1        = 4'h1;
  localparam    DS_2        = 4'h2;
  localparam    DS_3        = 4'h3;
  localparam    DS_4        = 4'h4;
  localparam    DS_5        = 4'h5;
  localparam    DS_6        = 4'h6;
  localparam    DS_7        = 4'h7;
  localparam    DS_8        = 4'h8;
  localparam    DS_9        = 4'h9;
  localparam    DS_A        = 4'ha;
  localparam    DS_B        = 4'hb;
  localparam    DS_C        = 4'hc;
  localparam    DS_D        = 4'hd;
  localparam    DS_E        = 4'he;
  localparam    DS_F        = 4'hf;

  localparam    PE_DIS      = 1'b0;
  localparam    PE_ENA      = 1'b1;

  localparam    PS_DN       = 1'b0;
  localparam    PS_UP       = 1'b1;

  localparam    PU_DIS      = 1'b0;
  localparam    PU_ENA      = 1'b1;

  localparam    PD_DIS      = 1'b0;
  localparam    PD_ENA      = 1'b1;

  localparam    ST_DIS      = 1'b0;
  localparam    ST_ENA      = 1'b1;

  localparam    IE_DIS      = 1'b0;
  localparam    IE_ENA      = 1'b1;

  localparam    XE_DIS      = 1'b0;
  localparam    XE_ENA      = 1'b1;

  // Test Input I/O configuration
  localparam    TI_OEN      = OE_DIS;
  localparam    TI_DS       = DS_0;
  localparam    TI_PE_PU    = PE_DIS;
  localparam    TI_PS_PD    = PS_DN;
  localparam    TI_ST       = ST_DIS;
  localparam    TI_IE       = IE_ENA;
  localparam    TI_I        = TIE_L;

  // Test Output I/O configuration
  localparam    TO_OEN      = OE_ENA;
  localparam    TO_DS       = DS_8;
  localparam    TO_PE_PU    = PE_DIS;
  localparam    TO_PS_PD    = PS_DN;
  localparam    TO_ST       = ST_DIS;
  localparam    TO_IE       = IE_DIS;
endpackage : gpio_pkg
```
- 이러한 상수들은 `iomux.py`가 생성하는 코드에서 하드코딩되지 않고, `gpio_pkg`로부터 import 되어 사용된다.

----

 - **B101**: 버스 인덱스 **불연속** — 사용된 인덱스가 0..W-1 연속이 아님
 - **B102**: 버스 **스칼라/인덱스 혼용** — 동일 base에서 스칼라와 인덱스 표기를 함께 사용
 - **B103**: 버스 인덱스 **중복 정의(동일 서브모드)**
 - **F101**: 엑셀 병합 포맷 오류(필수 머지/헤더 누락)
 - **F102**: 모드/서브모드/OM 헤더 탐지 실패
 - **F103**: `Pin Name` 중복
 - **F104**: mode/sub_mode 블록 시작 또는 내부에 **빈 셀 존재** (STRICT)
 - **F105**: mode/sub_mode **병합 불연속** — 중간에 비머지/빈 셀/공백 행·열 존재 (STRICT)
 - **P201**: `-pad_type` 미지정
 - **P202**: I-only PAD에 O/IO 지정
 - **P203**: 금지 핀(OM/XIN/XOUT/PORn)에 MUX 정의됨
 - **O301**: OM 값 범위 초과
 - **O302**: OM 값 중복(서브모드 간)
 - **O304**: 동일 서브모드에서 OM 정의가 충돌됨
 - **C402**: enable **베이스 불일치** — `signal / enable` 쌍에서 enable 이름의 **베이스가 다름** (예: `TDO / TDI_oen` → 오류)
 - **C403**: OE 네이밍 규칙 위반(`oe`/`oen`/`oe_n`/`oen_n`)
 - **C404**: GPIO-like 제어 누락
 - **S701**: `-mux_exclude`인데 엑셀에 정의 존재
 - **S702**: `test_en`↔모드 enable 비트 미연결
 - **U902**: 동일 base에 입력/출력 혼용
 - **U903**: 동일 신호가 서브모드 간 **버스폭 불일치**
 - **F106**: §3.2 위반 — 우측 3열 배치/값 오류(잘못된 값, 위치 불일치, 빈 칸인데 다른 열에 기입됨)

모든 에러는 메시지와 함께 **즉시 종료**한다.

----

## 12) 버전/생성 정보 각인 (Version Stamping)
모든 생성 RTL(`{sub_mode}.sv`, `{mode}_mux.sv`, `pad_mux.sv`)의 최상단에 **툴 버전/생성 정보**를 주석으로 각인한다.

**포맷**
```verilog
// Auto-generated by iomux_gen v<MAJOR.MINOR.PATCH>
// Generated at <YYYY-MM-DD HH:MM:SS>
// input: <엑셀 파일명>
// sheet: <시트 이름>
// NI: <입력 PAD 개수>
// NO: <IO PAD 개수>
```

-	시각은 로컬 시스템 시간으로 기록한다.
-	NI/NO는 pad_mux.sv 기준의 PAD 개수이다.
-	이 정보는 디버깅(“어떤 버전으로 언제 생성했는가”) 시 기준선을 제공한다.

## 13) 실행 방법 (CLI)
```bash
python iomux_gen.py \
  -i Kameleon_operation_mode_and_test_multiplexing.xlsx \
  -o out \
  -pad_type PDIDWUWSWCDG I \
  -pad_type PDDWUWSWCDG IO \
  -mux_exclude OM -mux_exclude XIN -mux_exclude XOUT -mux_exclude PORn
# --sheet 미지정 시 자동 탐색
```
출력 디렉터리에 `pad_mux.sv`, 각 모드의 `*_mux.sv`, 그리고 모든 `{sub_mode}.sv`가 생성된다.

---

## 14) 참고
- 향후 확장: Reset(R) 마커 동작 정의, GPIO-like 대소문자 처리 정책, `io_test` 자동화 로직 등.
