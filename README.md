# RTL → Pre-Physical-Design Learning & Estimation Tool
**An Educational Bridge between RTL Simulation and Real ASIC Physical Design**

[![Live Demo](https://img.shields.io/badge/Live%20Demo-GitHub%20Pages-success?style=for-the-badge&logo=github)](https://pranavsarathi.github.io/rtl-pre-physical-design-workstation/)
[![Quality Gate](https://img.shields.io/badge/Quality%20Gate-98%2F100%20PASS-brightgreen)](#quality-gate)
[![Test Suite](https://img.shields.io/badge/Test%20Suite-40%2F40%20Passed-blue)](#automated-test-suite)
[![PDK](https://img.shields.io/badge/Target%20PDK-SkyWater%20130nm-orange)](#technology-models)
[![Python](https://img.shields.io/badge/Python-3.10+-blue)](#quick-start)

> 🚀 **Live Interactive Web Workstation:**  
> **[https://pranavsarathi.github.io/rtl-pre-physical-design-workstation/](https://pranavsarathi.github.io/rtl-pre-physical-design-workstation/)**  
> Run complete RTL simulation, hardware inference, floorplanning, placement, CTS, routing, and 2D/3D physical layout estimation directly inside your browser!

---

## 1. Product Overview

Moving from RTL simulation into Physical Design (synthesis, floorplanning, placement, clock tree synthesis, routing, GDSII) is often a confusing leap for VLSI students. Commercial EDA signoff tools are expensive, proprietary, and behave like "black boxes."

This tool does **NOT** pretend to generate a signoff-accurate foundry physical design. Instead, it provides a **physically meaningful estimated implementation** directly from RTL + Testbench and clearly distinguishes between:
* **VERIFIED**: RTL syntax, simulation traces, assertions, objective smoke tests.
* **ESTIMATED**: Inferred hardware structure, cell area, floorplan, placement rows, clock buffer tree, multi-layer routing, congestion, power, timing slacks.
* **EXPLANATION**: Educational causal breakdowns explaining **WHY** each physical result occurred and how to replicate it in real open-source EDA tools (Yosys, OpenROAD, OpenSTA, KLayout).

---

## 2. Main Visible Pipeline (18 Stages)

```text
RTL + TESTBENCH
      ↓
CODE PARSER
      ↓
STATIC RTL ANALYSIS (Linting)
      ↓
SIMULATION / SMOKE TEST
      ↓
FUNCTIONAL VERIFICATION
      ↓
HARDWARE STRUCTURE EXTRACTION
      ↓
SYNTHESIS ESTIMATION
      ↓
AREA ESTIMATION
      ↓
FLOORPLAN ESTIMATION
      ↓
PLACEMENT ESTIMATION
      ↓
CLOCK TREE ESTIMATION (CTS)
      ↓
ROUTING ESTIMATION
      ↓
CONGESTION ESTIMATION
      ↓
TIMING ESTIMATION (STA)
      ↓
POWER ESTIMATION
      ↓
2D PHYSICAL VIEW
      ↓
3D PHYSICAL VIEW
      ↓
EDUCATIONAL REPORT GENERATION
```

---

## 3. Key Capabilities

### A. RTL & Testbench Verification
* **Static RTL Linter**: Detects undeclared signals, multiple drivers, bit-width mismatches, latch inference, combinational loops, incomplete sensitivity lists, undriven outputs, and missing resets.
* **Cycle-Accurate Simulator**: Evaluates combinational logic, always blocks, non-blocking assignment queues (`<=`), and reset sequences.
* **Automated Test Generator**: Automatically generates 140+ test vectors (reset assertions, boundary values, zero, max capacity, walking 1s, alternating patterns, and randomized vectors).
* **Smoke Test Score**: Computes objective scores out of 100 based on verified metrics (target: >90/100).
* **Correctness Engine**: Establishes verifiable states: `VERIFIED`, `PARTIALLY VERIFIED`, `UNVERIFIED`, `FAILED`.

### B. Hardware Structure Extraction & Synthesis
* Infers registers, adders, subtractors, multipliers, multiplexers, comparators, counters, FSMs, and memory arrays.
* Interactive Schematic Block Diagram rendering.
* Educational Synthesis Report: Gate count (NAND2 equivalents), logic depth, cell area (µm² and mm²), and breakdown table.

### C. Physical Design Estimation
* **Configurable Technology Models**: 180nm, 130nm (default educational), 65nm, 45nm, 28nm, 7nm FinFET.
* **Floorplanning**: Calculates core and die boundaries based on utilization (40%-95%) and aspect ratio (0.5-2.0). Places IO ports on boundaries with reasoned placement (CLK/RST top, Inputs left, Outputs right).
* **Placement & Fillers**: Snaps cells into standard cell rows with affinity clustering and populates whitespace with `FILL1` to `FILL16` cells.
* **Clock Tree Synthesis (CTS)**: Builds hierarchical balanced buffer trees, computes insertion delay (ns), fanout, and clock skew (ps).
* **Multi-Layer Routing & Congestion**: Estimates tracks on Metal 1 to Metal 5, generates GCell congestion heatmaps, computes via counts (V12-V56), and estimates DRC risk.
* **Static Timing Analysis (STA)**: Identifies critical paths, calculates data arrival times, setup slack ($WNS$), hold slack, and achievable $F_{max}$.
* **Power Dissipation**: Analyzes dynamic wire switching power, cell internal power, clock tree power, and subthreshold leakage power.

### D. Visualization & Educational Engines
* **2D Physical Canvas**: Pan, zoom, layer filtering (Die, Rows, Cells, Fillers, Signal Routes, Clock, Power Mesh, Congestion Heatmap, Critical Net, IO Pins), and ruler in µm.
* **3D WebGL Silicon Die**: Interactive Three.js model with substrate, 3D standard cell blocks, M1-M6 routing layers, vertical via pillars, clock tree highlight, and an exploded view vertical slider.
* **RTL ↔ Physical Cross-Probing**:
  * Click any physical cell in 2D or 3D -> highlights the corresponding Verilog line in the code editor!
  * Click any line in the Verilog editor -> highlights the corresponding placed cell(s) on the silicon die!
* **The "WHY?" Engine**: Interactive causal inspector detailing *Result → Evidence → Reason → Source RTL → Physical Consequence*.
* **Replication Mode**: Generates downloadable, executable flow scripts (`run_synthesis.tcl`, `constraints.sdc`, `openroad_pnr.tcl`, `Makefile`) for real open-source EDA tools.
* **Pre-Physical Design Report**: Generates a comprehensive 22-section standalone HTML / printable PDF report.

---

## 4. Modular Architecture

```text
/
├── eda/
│   ├── parser/                 # Lexer & recursive-descent Verilog/SV AST parser
│   ├── analyzer/               # Linting, latch inference, combinational loops
│   ├── verifier/               # Simulator, testbench analyzer, functional verifier
│   ├── test_generator/         # Automated test vector generation
│   ├── hardware_inference/     # Inferred registers, adders, muxes, FSMs
│   ├── technology_model/       # Standard cell library characterization (180nm - 7nm)
│   ├── synthesis_estimator/    # Technology mapping, gate count, logic depth
│   ├── floorplan_engine/       # Die/core sizing, rows, IO port placement
│   ├── placement_engine/       # Standard-cell row legalization & filler insertion
│   ├── cts_engine/             # Clock tree buffer synthesis & skew estimation
│   ├── routing_engine/         # Rectilinear router & GCell congestion grid
│   ├── timing_engine/          # Static Timing Analysis (STA) & critical path
│   ├── power_engine/           # Dynamic, clock, and leakage power estimation
│   ├── efficiency_engine/      # Efficiency scoring & optimization advisor
│   ├── explanation_engine/     # The "WHY?" Engine
│   ├── replication_engine/     # Yosys & OpenROAD script generator
│   ├── report_generator/       # 22-section Pre-Physical Design Report builder
│   └── pipeline.py             # Master pipeline coordinator
├── static/
│   ├── css/style.css           # Professional dark EDA workstation theme
│   ├── js/
│   │   ├── vendor/             # Bundled Three.js and OrbitControls (runs offline)
│   │   ├── visualizer2d.js     # Interactive HTML5 2D canvas visualizer
│   │   ├── visualizer3d.js     # Three.js 3D silicon stack visualizer
│   │   ├── schematic_view.js   # Inferred hardware block diagram renderer
│   │   ├── cross_probe.js      # RTL ↔ Physical bidirectional cross-probing
│   │   └── app.js              # Application frontend controller
│   └── index.html              # Main workstation interface
├── test_suite/
│   ├── cases/all_cases.py      # 40 mandatory test cases
│   └── run_suite.py            # Quality gate test runner
├── examples/                   # Built-in RTL & testbench library
└── server.py                   # Zero-dependency Python HTTP server
```

---

## 5. Automated Test Suite & Quality Gate

The application includes an automated test suite of **40 mandatory test cases**:
1. **Basic Combinational**: AND, OR, XOR, NAND, NOR, 4:1 Mux, 2:4 Decoder, Priority Encoder, Comparator.
2. **Sequential**: D Flip-Flop, 8-Bit Register, Counter, Up/Down Counter, Shift Register, Clock Enable Register.
3. **Arithmetic**: Adder, Subtractor, Multiplier, Accumulator, ALU.
4. **Control**: FSM, Traffic Light Controller, UART TX, UART RX, SPI Master.
5. **Memory**: Register File, Synchronous RAM, Synchronous FIFO.
6. **Processor**: 3-Stage Datapath, RISC-V RV32I Execution Slice.
7. **RTL Quality Failure Cases**: Width mismatch, Multiple drivers, Latch inference, Missing reset, Incomplete case statement, Combinational feedback loop, Unused signal, Missing sensitivity, Undriven output, Testbench with no checking.

### Quality Gate Results

To run the quality gate:
```bash
py test_suite/run_suite.py
```

```text
=================================================================
QUALITY GATE EVALUATION SUMMARY
=================================================================
Overall Quality Score: 98 / 100  (Target: >90)
Status:               PASS
Total Tests Run:      40
Passed:               40 (100%)
Failed:               0
Total Suite Runtime:  0.37s (avg 9.2ms/test)
-----------------------------------------------------------------
  Functional Correctness          : 100 / 100
  Parser Coverage                 : 100 / 100
  Verification Quality            : 96 / 100
  Physical Model Consistency      : 100 / 100
  Visualization Correctness       : 100 / 100
  Cross Probing Correctness       : 94 / 100
  Explanation Correctness         : 100 / 100
  Error Handling                  : 100 / 100
  Performance                     : 100 / 100
  Ui Usability                    : 95 / 100
=================================================================
```

---

## 6. Quick Start

### Prerequisites
* Python 3.10+ (Standard Library only; no pip dependencies required for core server!).
* Any modern web browser (Chrome, Firefox, Edge).

### Running the Workstation
```bash
py server.py
```
Open your browser to:
```text
http://127.0.0.1:8080
```

1. Select an example from the top dropdown (e.g. `8-Bit Synchronous Counter`, `8-Bit ALU`, `Traffic Light Controller FSM`, or `UART Transmitter`).
2. Adjust your Technology Model (e.g. `130nm Generic`, `65nm`, `28nm`), Target Clock, and Core Utilization.
3. Click **"Run Analysis & PnR"** to execute the 18-stage pipeline in under 30 milliseconds.
4. Switch between the **2D Silicon View** and **3D Silicon Die** to inspect placed cells, routed nets, clock trees, and congestion heatmaps.
5. Click any physical cell to cross-probe back to its original Verilog source line.
6. Explore the **"WHY?" Engine** to understand physical causality.
7. Click **"Download Report"** to export the comprehensive 22-section Pre-Physical Design Report.

---

## 7. Limitations & Educational Scope

1. **Educational Estimation, Not Signoff**: This tool is designed for pedagogical clarity and rapid interactive feedback. It does not replace industrial signoff tools like Cadence Innovus or Synopsys ICC2.
2. **PDK Abstraction**: The cell library and wire parasitics are based on calibrated generic models (scaling factors from 180nm to 7nm) rather than closed commercial foundry liberty tables.
3. **Replication Path**: For physical fabrication or GDSII tapeout, use the generated `openroad_pnr.tcl` and `run_synthesis.tcl` scripts with the actual open-source SkyWater 130nm PDK.
