# Educational Synthesis Estimator
from typing import Dict, List, Any
import math
from eda.hardware_inference.inferencer import HardwareInferencer
from eda.technology_model.tech_library import TechnologyModel, StandardCell

class SynthesisInstance:
    def __init__(self, inst_name: str, cell: StandardCell, block_ref: str, rtl_line: int = 1):
        self.inst_name = inst_name
        self.cell = cell
        self.block_ref = block_ref
        self.rtl_line = rtl_line

    def to_dict(self) -> Dict[str, Any]:
        return {
            "inst_name": self.inst_name,
            "cell_type": self.cell.name,
            "function": self.cell.function,
            "area_um2": self.cell.area_um2,
            "width_um": self.cell.width_um,
            "height_um": self.cell.height_um,
            "block_ref": self.block_ref,
            "rtl_line": self.rtl_line
        }

class SynthesisEstimator:
    def __init__(self, inference_data: Dict[str, Any], tech: TechnologyModel):
        self.inference = inference_data
        self.tech = tech
        self.instances: List[SynthesisInstance] = []

    def estimate(self) -> Dict[str, Any]:
        self.instances.clear()
        cells = self.tech.cells

        seq_cells = 0
        comb_cells = 0
        inst_idx = 0

        # Breakdown counters
        count_reg = 0
        count_mux = 0
        count_adder = 0
        count_cmp = 0
        count_gate = 0
        count_buf = 0
        count_clock = 0

        # 1. Map sequential registers & counters
        for b in self.inference.get("blocks", []):
            b_type = b["block_type"]
            w = b["width"]
            line = b["rtl_line"]

            if b_type == "REGISTER":
                for bit in range(w):
                    inst_idx += 1
                    inst = SynthesisInstance(f"U_REG_{inst_idx}", cells["DFFR_X1"], b["name"], line)
                    self.instances.append(inst)
                    seq_cells += 1
                    count_reg += 1

            elif b_type == "COUNTER":
                # A counter synthesizes into registers + adders/incrementers + enable logic
                for bit in range(w):
                    inst_idx += 1
                    inst = SynthesisInstance(f"U_CTR_REG_{inst_idx}", cells["DFFRE_X1"], b["name"], line)
                    self.instances.append(inst)
                    seq_cells += 1
                    count_reg += 1
                # Incrementer logic: w Half Adders / Full Adders + XORs
                for bit in range(w):
                    inst_idx += 1
                    c_cell = cells["HA_X1"] if bit == 0 else cells["FA_X1"]
                    self.instances.append(SynthesisInstance(f"U_CTR_ADD_{inst_idx}", c_cell, b["name"], line))
                    comb_cells += 1
                    count_adder += 1

            elif b_type in ("ADDER", "SUBTRACTOR"):
                # w-bit ripple-carry or CLA: roughly w Full Adders
                for bit in range(w):
                    inst_idx += 1
                    self.instances.append(SynthesisInstance(f"U_ADD_{inst_idx}", cells["FA_X1"], b["name"], line))
                    comb_cells += 1
                    count_adder += 1
                if b_type == "SUBTRACTOR":
                    # Inverters on operand B
                    for bit in range(w):
                        inst_idx += 1
                        self.instances.append(SynthesisInstance(f"U_INV_{inst_idx}", cells["INV_X1"], b["name"], line))
                        comb_cells += 1
                        count_gate += 1

            elif b_type == "MULTIPLIER":
                # w x w multiplier: roughly w*(w-1) Full Adders and w*w AND gates
                fa_cnt = w * max(1, w - 1)
                and_cnt = w * w
                for _ in range(fa_cnt):
                    inst_idx += 1
                    self.instances.append(SynthesisInstance(f"U_MUL_FA_{inst_idx}", cells["FA_X1"], b["name"], line))
                    comb_cells += 1
                    count_adder += 1
                for _ in range(and_cnt):
                    inst_idx += 1
                    self.instances.append(SynthesisInstance(f"U_MUL_AND_{inst_idx}", cells["AND2_X1"], b["name"], line))
                    comb_cells += 1
                    count_gate += 1

            elif b_type == "COMPARATOR":
                # w XORs + tree of ANDs/NORs
                for _ in range(w):
                    inst_idx += 1
                    self.instances.append(SynthesisInstance(f"U_CMP_XOR_{inst_idx}", cells["XOR2_X1"], b["name"], line))
                    comb_cells += 1
                    count_cmp += 1
                tree_gates = max(1, w - 1)
                for _ in range(tree_gates):
                    inst_idx += 1
                    self.instances.append(SynthesisInstance(f"U_CMP_AND_{inst_idx}", cells["AND2_X1"], b["name"], line))
                    comb_cells += 1
                    count_cmp += 1

            elif b_type == "MUX":
                inps = b.get("details", {}).get("inputs", 2)
                # 2:1 mux is w MUX2 cells. 4:1 is 3*w MUX2 cells.
                num_mux2 = (inps - 1) * w
                for _ in range(num_mux2):
                    inst_idx += 1
                    self.instances.append(SynthesisInstance(f"U_MUX_{inst_idx}", cells["MUX2_X1"], b["name"], line))
                    comb_cells += 1
                    count_mux += 1

            elif b_type == "GATE":
                gate_fn = b.get("details", {}).get("gate", "AND")
                target_cell = cells["AND2_X1"]
                if gate_fn == "OR": target_cell = cells["OR2_X1"]
                elif gate_fn == "XOR": target_cell = cells["XOR2_X1"]
                elif gate_fn == "NOT": target_cell = cells["INV_X1"]
                for _ in range(w):
                    inst_idx += 1
                    self.instances.append(SynthesisInstance(f"U_GATE_{inst_idx}", target_cell, b["name"], line))
                    comb_cells += 1
                    count_gate += 1

            elif b_type == "FSM":
                state_reg = b.get("details", {}).get("state_reg")
                state_w = b.get("details", {}).get("state_width", w)
                state_cnt = b.get("details", {}).get("state_count", 4)
                # Only instantiate state flip-flops if not already instantiated by a sequential REGISTER block
                has_reg_block = any(other["block_type"] == "REGISTER" and other.get("details", {}).get("target") == state_reg for other in self.inference.get("blocks", []))
                if not has_reg_block:
                    for _ in range(state_w):
                        inst_idx += 1
                        self.instances.append(SynthesisInstance(f"U_FSM_REG_{inst_idx}", cells["DFFR_X1"], b["name"], line))
                        seq_cells += 1
                        count_reg += 1
                # Next state combinational logic & output decoder: ~ 3-5 gates per state
                for _ in range(state_cnt * 4):
                    inst_idx += 1
                    self.instances.append(SynthesisInstance(f"U_FSM_LOGIC_{inst_idx}", cells["NAND2_X1"], b["name"], line))
                    comb_cells += 1
                    count_gate += 1

            elif b_type == "MEMORY":
                depth = b.get("details", {}).get("depth", 16)
                # Small memory modeled as register file
                for _ in range(min(depth, 32) * w):
                    inst_idx += 1
                    self.instances.append(SynthesisInstance(f"U_MEM_BIT_{inst_idx}", cells["DFFRE_X1"], b["name"], line))
                    seq_cells += 1
                    count_reg += 1
                # Read address decoder
                for _ in range(depth):
                    inst_idx += 1
                    self.instances.append(SynthesisInstance(f"U_MEM_DEC_{inst_idx}", cells["AND2_X1"], b["name"], line))
                    comb_cells += 1
                    count_gate += 1

        # Buffers: add input/output drive buffers (approx 1 per 5 cells)
        count_buf = max(2, int(round((seq_cells + comb_cells) * 0.08)))
        for _ in range(count_buf):
            inst_idx += 1
            self.instances.append(SynthesisInstance(f"U_BUF_{inst_idx}", cells["BUF_X1"], "IO_BUF", 1))
            comb_cells += 1

        # Clock-related cells (tree buffers)
        count_clock = max(1, int(math.ceil(seq_cells / 8.0))) if seq_cells > 0 else 0
        for _ in range(count_clock):
            inst_idx += 1
            self.instances.append(SynthesisInstance(f"U_CLKBUF_{inst_idx}", cells["CLKBUF_X8"], "CTS_BUF", 1))

        # Calculate Area
        total_cell_area_um2 = sum(inst.cell.area_um2 for inst in self.instances)
        seq_area_um2 = sum(inst.cell.area_um2 for inst in self.instances if inst.cell.function in ("DFF", "DFFR", "DFFRE"))
        comb_area_um2 = total_cell_area_um2 - seq_area_um2
        area_mm2 = total_cell_area_um2 / 1_000_000.0

        # Equivalent Gate Count (NAND2 Equivalent)
        nand2_area = cells["NAND2_X1"].area_um2
        gate_count = int(round(total_cell_area_um2 / max(0.1, nand2_area)))

        # Logic Depth & Critical Path Estimation
        # Typical logic depth through adder/arithmetic or mux tree
        logic_depth = 2
        if count_adder > 0:
            logic_depth += int(math.log2(max(2, count_adder)) * 3) + 4
        elif count_cmp > 0:
            logic_depth += int(math.log2(max(2, count_cmp)) * 2) + 3
        elif count_mux > 0:
            logic_depth += int(math.log2(max(2, count_mux)) * 2) + 2
        else:
            logic_depth += min(6, max(1, comb_cells // 4))

        # Delay = Clk-to-Q + (Logic_depth * avg_gate_delay) + setup_time
        avg_gate_delay_ps = (cells["NAND2_X1"].intrinsic_delay_ps + cells["AND2_X1"].intrinsic_delay_ps) / 2.0
        clk_to_q_ps = cells["DFFR_X1"].intrinsic_delay_ps
        setup_time_ps = 80.0 * self.tech.info["scale_factor"]
        wire_delay_est_ps = logic_depth * 25.0 * self.tech.info["scale_factor"]

        critical_path_ps = clk_to_q_ps + (logic_depth * avg_gate_delay_ps) + wire_delay_est_ps + setup_time_ps
        critical_path_ns = round(critical_path_ps / 1000.0, 3)

        # Fmax calculation (MHz)
        estimated_fmax_mhz = int(round(1000.0 / max(0.5, critical_path_ns)))

        cell_counts = {}
        for inst in self.instances:
            cell_counts[inst.cell.name] = cell_counts.get(inst.cell.name, 0) + 1

        return {
            "estimation_label": "ESTIMATED SYNTHESIS (Pre-Physical Design)",
            "technology_node": self.tech.node,
            "sequential_elements": seq_cells,
            "combinational_cells": comb_cells,
            "clock_cells": count_clock,
            "other_cells": count_clock,
            "total_cells": seq_cells + comb_cells + count_clock,
            "estimated_cell_area_um2": round(total_cell_area_um2, 2),
            "cell_area_um2": round(total_cell_area_um2, 2),
            "estimated_logic_area_mm2": round(area_mm2, 6),
            "sequential_area_um2": round(seq_area_um2, 2),
            "combinational_area_um2": round(comb_area_um2, 2),
            "gate_count_nand2_equiv": gate_count,
            "cell_counts": cell_counts,
            "breakdown": {
                "registers": count_reg,
                "muxes": count_mux,
                "adders": count_adder,
                "comparators": count_cmp,
                "logic_gates": count_gate,
                "buffers": count_buf,
                "clock_cells": count_clock
            },
            "logic_depth": logic_depth,
            "critical_path_ns": critical_path_ns,
            "estimated_fmax_mhz": estimated_fmax_mhz,
            "instances": [inst.to_dict() for inst in self.instances]
        }
