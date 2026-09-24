# Open-Source Real EDA Replication Script & Workflow Generator
from typing import Dict, List, Any

class ReplicationScriptGenerator:
    def __init__(self, top_module_name: str, tech_node: str = "130nm", clock_mhz: float = 100.0,
                 core_util: float = 0.70, aspect_ratio: float = 1.0):
        self.top = top_module_name or "top"
        self.tech_node = tech_node
        self.clock_mhz = clock_mhz
        self.clock_period_ns = round(1000.0 / max(1.0, clock_mhz), 3)
        self.core_util = int(round(core_util * 100))
        self.aspect_ratio = aspect_ratio

    def generate_all(self) -> Dict[str, Any]:
        return {
            "steps": self._generate_workflow_steps(),
            "scripts": {
                "run_synthesis.tcl": self._generate_yosys_tcl(),
                "constraints.sdc": self._generate_sdc(),
                "openroad_pnr.tcl": self._generate_openroad_tcl(),
                "Makefile": self._generate_makefile(),
                "sim_iverilog.sh": self._generate_iverilog_sh()
            }
        }

    def _generate_workflow_steps(self) -> List[Dict[str, Any]]:
        return [
            {
                "step_num": 1,
                "title": "RTL Functional Verification",
                "tool_category": "RTL Simulator (Icarus Verilog / Verilator)",
                "required_input": f"{self.top}.v, tb_{self.top}.v",
                "expected_output": f"{self.top}.vvp simulation binary, wave.vcd waveform dump",
                "inspection_guide": "Open wave.vcd in GTKWave to confirm all internal state transitions and verify that assertion statements pass without error.",
                "example_command": f"iverilog -o sim.vvp {self.top}.v tb_{self.top}.v && vvp sim.vvp -vcd"
            },
            {
                "step_num": 2,
                "title": "RTL Logic Synthesis",
                "tool_category": "Logic Synthesizer (Yosys Open Synthesis Suite)",
                "required_input": f"{self.top}.v, sky130_fd_sc_hd__tt_025C_1v80.lib",
                "expected_output": f"{self.top}_synth.v gate-level netlist, synthesis area statistics",
                "inspection_guide": "Inspect {self.top}_synth.v to verify that all registers mapped to target PDK flip-flops (DFF) and that no unexpected latches were inferred.",
                "example_command": f"yosys -c run_synthesis.tcl"
            },
            {
                "step_num": 3,
                "title": "Floorplanning & IO Pin Placement",
                "tool_category": "Physical Design Engine (OpenROAD)",
                "required_input": f"{self.top}_synth.v, constraints.sdc, tech.lef, stdcells.lef",
                "expected_output": "Die & core boundary initialized, standard cell rows created, IO pins placed",
                "inspection_guide": "Confirm die aspect ratio and verify that IO pins are distributed cleanly around the core without shorts.",
                "example_command": "openroad -exit openroad_pnr.tcl"
            },
            {
                "step_num": 4,
                "title": "Power Distribution Network (PDN)",
                "tool_category": "Power Grid Generator (OpenROAD pdngen)",
                "required_input": "Core floorplan, standard cell row sites",
                "expected_output": "Metal 1 follow-pin rails, Metal 4/Metal 5/Metal 6 power stripes & rings",
                "inspection_guide": "Check VDD and VSS straps spacing to ensure low IR-drop across the standard cell array.",
                "example_command": "define_pdn_grid -name stdcell_grid ..."
            },
            {
                "step_num": 5,
                "title": "Global & Detailed Placement",
                "tool_category": "Standard Cell Placer (OpenROAD RePlAce & DPL)",
                "required_input": "Floorplan with PDN, gate-level netlist",
                "expected_output": "Legalized standard-cell placement, no cell overlaps, filler cells inserted",
                "inspection_guide": "Inspect standard cell density heatmap in OpenROAD GUI; ensure peak utilization does not exceed 85%.",
                "example_command": "global_placement -density 0.70; detailed_placement"
            },
            {
                "step_num": 6,
                "title": "Clock Tree Synthesis (CTS)",
                "tool_category": "Clock Tree Synthesizer (OpenROAD TritonCTS)",
                "required_input": "Placed netlist, clock tree buffer library",
                "expected_output": "Balanced clock buffer tree, inserted CLKBUF cells, routed clock trunk",
                "inspection_guide": "Inspect report_clock_tree to verify maximum skew (< 50 ps) and clock insertion delay.",
                "example_command": "clock_tree_synthesis -root_buf sky130_fd_sc_hd__clkbuf_16"
            },
            {
                "step_num": 7,
                "title": "Global & Detailed Routing",
                "tool_category": "Routing Engine (OpenROAD FastRoute & TritonRoute)",
                "required_input": "Placed & CTS-buffered design, LEF design rules",
                "expected_output": "Detailed routed nets on Metal 1 to Metal 5, zero DRC shorts",
                "inspection_guide": "Run check_drc to confirm 0 DRC violations and zero antenna rule violations.",
                "example_command": "global_route; detailed_route"
            },
            {
                "step_num": 8,
                "title": "Signoff Static Timing Analysis (STA)",
                "tool_category": "Static Timing Analyzer (OpenSTA)",
                "required_input": "Post-route netlist, SPEF parasitic extraction, constraints.sdc, .lib",
                "expected_output": "Worst Negative Slack (WNS), Total Negative Slack (TNS), setup/hold checks",
                "inspection_guide": "Ensure WNS >= 0.00 ns for setup and hold timing closure across all corners (TT, SS, FF).",
                "example_command": "report_checks -path_delay min_max -fields {input_pin slew cap}"
            },
            {
                "step_num": 9,
                "title": "Physical Verification & GDSII Streaming",
                "tool_category": "Layout & Verification (Magic / KLayout)",
                "required_input": "Final DEF file, standard cell GDSII library",
                "expected_output": f"{self.top}.gds layout stream file ready for foundry photomask generation",
                "inspection_guide": "Open {self.top}.gds in KLayout; verify seal ring, layer numbers, and macro placement.",
                "example_command": f"write_gds {self.top}.gds"
            }
        ]

    def _generate_yosys_tcl(self) -> str:
        return f"""# ==============================================================================
# Yosys Logic Synthesis Script for {self.top}
# Target PDK: SkyWater 130nm / Generic CMOS Standard Cells
# ==============================================================================

# 1. Read Verilog RTL source files
read_verilog {self.top}.v

# 2. Elaborate module hierarchy
hierarchy -check -top {self.top}

# 3. High-level synthesis optimizations
proc
opt
fsm
opt
memory
opt

# 4. Map arithmetic operators to standard cell implementations
techmap
opt

# 5. Map flip-flops to target technology library
dfflibmap -liberty sky130_fd_sc_hd__tt_025C_1v80.lib

# 6. Map combinational logic using ABC
abc -liberty sky130_fd_sc_hd__tt_025C_1v80.lib

# 7. Clean up unused nets & generate area report
clean
stat -liberty sky130_fd_sc_hd__tt_025C_1v80.lib

# 8. Write synthesized gate-level netlist
write_verilog -noattr {self.top}_synth.v
"""

    def _generate_sdc(self) -> str:
        return f"""# ==============================================================================
# Synopsys Design Constraints (SDC) for {self.top}
# Target Frequency: {self.clock_mhz} MHz (Clock Period: {self.clock_period_ns} ns)
# ==============================================================================

# 1. Create primary clock constraint
create_clock -name clk -period {self.clock_period_ns} [get_ports clk]

# 2. Clock uncertainty and jitter
set_clock_uncertainty -setup 0.15 [get_clocks clk]
set_clock_uncertainty -hold 0.05 [get_clocks clk]
set_clock_transition 0.10 [get_clocks clk]

# 3. Input delays relative to clock (30% of clock period)
set_input_delay -clock clk {round(self.clock_period_ns * 0.3, 3)} [all_inputs -no_clocks]

# 4. Output delays relative to clock (30% of clock period)
set_output_delay -clock clk {round(self.clock_period_ns * 0.3, 3)} [all_outputs]

# 5. Output pin capacitance load (10 fF typical external load)
set_load 0.010 [all_outputs]
"""

    def _generate_openroad_tcl(self) -> str:
        return f"""# ==============================================================================
# OpenROAD Physical Design Automation Script for {self.top}
# Automated Flow: Floorplan -> PDN -> Place -> CTS -> Route -> STA -> GDSII
# ==============================================================================

# 1. Read Technology & Standard Cell LEFs
read_lef sky130_fd_sc_hd.tlef
read_lef sky130_fd_sc_hd.lef

# 2. Read Synthesized Gate-Level Netlist
read_verilog {self.top}_synth.v
link_design {self.top}

# 3. Read Timing Constraints
read_sdc constraints.sdc

# 4. Floorplanning: Set utilization ({self.core_util}%) and aspect ratio ({self.aspect_ratio})
initialize_floorplan -utilization {self.core_util} \\
                     -aspect_ratio {self.aspect_ratio} \\
                     -core_space 10.0 \\
                     -site unithd

# 5. Place IO Pins along boundaries
place_pins -hor_layer met3 -ver_layer met4

# 6. Power Distribution Network (PDN) Generation
source pdn_config.tcl
pdngen

# 7. Global Placement with density optimization
global_placement -density 0.70 -pad_left 2 -pad_right 2

# 8. Detailed Placement & Legalization
detailed_placement

# 9. Clock Tree Synthesis (CTS)
clock_tree_synthesis -root_buf sky130_fd_sc_hd__clkbuf_16 \\
                     -buf_list {{sky130_fd_sc_hd__clkbuf_8 sky130_fd_sc_hd__clkbuf_4}}

# 10. Global Routing
global_route -guide_file {self.top}.guide

# 11. Detailed Routing (TritonRoute)
detailed_route -output_drc {self.top}_drc.rpt

# 12. Final Static Timing Analysis Report
report_checks -path_delay min_max -fields {{slew cap input_pin}} > timing_report.rpt

# 13. Export Def and Stream to GDSII
write_def {self.top}_final.def
write_gds {self.top}.gds
puts "Physical Design Flow Completed Successfully for {self.top}!"
exit
"""

    def _generate_makefile(self) -> str:
        return f"""# ==============================================================================
# Open-Source ASIC EDA Build Automation Makefile
# Target: {self.top}
# ==============================================================================

TOP = {self.top}
RTL = $(TOP).v
TB  = tb_$(TOP).v

all: sim synth pnr sta

sim:
\t@echo "--> Running RTL Simulation with Icarus Verilog..."
\tiverilog -o $(TOP)_sim.vvp $(RTL) $(TB)
\tvvp $(TOP)_sim.vvp

synth:
\t@echo "--> Running Logic Synthesis with Yosys..."
\tyosys -c run_synthesis.tcl

pnr:
\t@echo "--> Running Physical Design Flow with OpenROAD..."
\topenroad -exit openroad_pnr.tcl

sta:
\t@echo "--> Running Static Timing Analysis with OpenSTA..."
\tsta -exit -f sta_signoff.tcl

clean:
\trm -rf *.vvp *.vcd *_synth.v *.def *.gds *.rpt *.log
"""

    def _generate_iverilog_sh(self) -> str:
        return f"""#!/usr/bin/env bash
# RTL Simulation Script
echo "Compiling RTL and Testbench with Icarus Verilog..."
iverilog -g2012 -o {self.top}_sim.vvp {self.top}.v tb_{self.top}.v
echo "Executing simulation..."
vvp {self.top}_sim.vvp
echo "Simulation finished. Waveforms saved to wave.vcd (open in GTKWave)."
"""
