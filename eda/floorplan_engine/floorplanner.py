# Floorplanning & Port Placement Engine
from typing import Dict, List, Any, Optional
import math
from eda.technology_model.tech_library import TechnologyModel
from eda.parser.ast_nodes import ModuleNode

class PlacedPort:
    def __init__(self, name: str, direction: str, width: int, side: str,
                 x_um: float, y_um: float, layer: str, is_clock: bool,
                 cts_required: bool, estimated_fanout: int, reason: str):
        self.name = name
        self.direction = direction # 'input', 'output', 'inout'
        self.width = width
        self.side = side # 'top', 'bottom', 'left', 'right'
        self.x_um = x_um
        self.y_um = y_um
        self.layer = layer
        self.is_clock = is_clock
        self.cts_required = cts_required
        self.estimated_fanout = estimated_fanout
        self.reason = reason

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "direction": self.direction,
            "width": self.width,
            "side": self.side,
            "x_um": round(self.x_um, 2),
            "y_um": round(self.y_um, 2),
            "layer": self.layer,
            "is_clock": self.is_clock,
            "cts_required": self.cts_required,
            "estimated_fanout": self.estimated_fanout,
            "reason": self.reason
        }

class StandardCellRow:
    def __init__(self, index: int, y_um: float, height_um: float, width_um: float, orientation: str):
        self.index = index
        self.y_um = y_um
        self.height_um = height_um
        self.width_um = width_um
        self.orientation = orientation # 'R0' (N) or 'MX' (FS) for shared VDD/VSS

    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "y_um": round(self.y_um, 2),
            "height_um": round(self.height_um, 2),
            "width_um": round(self.width_um, 2),
            "orientation": self.orientation
        }

class FloorplanEngine:
    def __init__(self, synthesis_data: Dict[str, Any], tech: TechnologyModel, module: ModuleNode):
        self.synth = synthesis_data
        self.tech = tech
        self.module = module
        self.ports: List[PlacedPort] = []
        self.rows: List[StandardCellRow] = []
        self.macros: List[Dict[str, Any]] = []

    def plan(self) -> Dict[str, Any]:
        self.ports.clear()
        self.rows.clear()
        self.macros.clear()

        # 1. Core Area calculation strictly derived from synthesized standard cells
        cell_area_um2 = max(5.0, float(self.synth.get("estimated_cell_area_um2", 10.0)))
        target_util = self.tech.core_utilization
        core_area_um2 = cell_area_um2 / target_util
        aspect_ratio = self.tech.aspect_ratio

        # Width and Height of Core
        # Area = W * H, W / H = AR => W^2 = Area * AR => W = sqrt(Area * AR), H = W / AR
        core_width_um = math.sqrt(core_area_um2 * aspect_ratio)
        core_height_um = core_area_um2 / core_width_um

        # Snap to technology row height and site width
        row_h = self.tech.info["row_height_um"]
        site_w = self.tech.info["site_width_um"]

        num_rows = max(4, int(math.ceil(core_height_um / row_h)))
        core_height_um = round(num_rows * row_h, 2)
        core_width_um = round(math.ceil(core_width_um / site_w) * site_w, 2)
        actual_core_area = round(core_width_um * core_height_um, 2)
        actual_utilization = round((cell_area_um2 / actual_core_area) * 100, 1)

        # Die Margin (for IO pads, seal ring, power rings)
        die_margin_um = max(10.0, round(row_h * 4.0, 2))
        die_width_um = round(core_width_um + 2 * die_margin_um, 2)
        die_height_um = round(core_height_um + 2 * die_margin_um, 2)
        die_area_um2 = round(die_width_um * die_height_um, 2)

        # 2. Generate Standard Cell Rows inside Core
        for r_idx in range(num_rows):
            y_pos = round(die_margin_um + (r_idx * row_h), 2)
            orient = "R0" if (r_idx % 2 == 0) else "MX"
            self.rows.append(StandardCellRow(r_idx, y_pos, row_h, core_width_um, orient))

        # 3. Detect and Place Macros / Memories
        mem_blocks = [b for b in self.synth.get("breakdown", {}) if b == "memories"]
        if self.synth.get("breakdown", {}).get("memories", 0) > 0 or any("RAM" in inst.get("cell_type", "") for inst in self.synth.get("instances", [])):
            macro_w = round(core_width_um * 0.35, 2)
            macro_h = round(core_height_um * 0.35, 2)
            self.macros.append({
                "name": "RAM_MACRO_0",
                "x_um": round(die_margin_um + core_width_um - macro_w - 5.0, 2),
                "y_um": round(die_margin_um + 5.0, 2),
                "width_um": macro_w,
                "height_um": macro_h,
                "type": "SRAM_MACRO",
                "halo_um": 3.0
            })

        # 4. Port Placement
        # Categorize ports: clock/reset on TOP, data in on LEFT, data out on RIGHT, control on BOTTOM
        top_ports = []
        left_ports = []
        right_ports = []
        bottom_ports = []

        seq_cells_cnt = self.synth.get("sequential_elements", 0)

        for p in self.module.ports:
            p_name_lower = p.name.lower()
            is_clk = "clk" in p_name_lower or "clock" in p_name_lower
            is_rst = "rst" in p_name_lower or "reset" in p_name_lower
            w = 1
            if p.width_msb:
                try:
                    w = abs(int(p.width_msb.raw if hasattr(p.width_msb, "raw") else getattr(p.width_msb, "value", 1))) + 1
                except Exception:
                    w = 8

            if is_clk:
                top_ports.append((p, w, is_clk, True, seq_cells_cnt, "Top edge placement provides balanced low-skew tree distribution across core."))
            elif is_rst:
                top_ports.append((p, w, is_clk, False, seq_cells_cnt, "Placed near clock to minimize reset distribution latency."))
            elif p.direction == "input":
                if "en" in p_name_lower or "sel" in p_name_lower or "valid" in p_name_lower or "ready" in p_name_lower:
                    bottom_ports.append((p, w, False, False, max(2, seq_cells_cnt // 4), "Control signals placed on bottom boundary for clean datapath segregation."))
                else:
                    left_ports.append((p, w, False, False, 2, "Data inputs placed on left edge for standard left-to-right datapath flow."))
            elif p.direction == "output":
                right_ports.append((p, w, False, False, 1, "Data outputs placed on right edge to terminate pipeline datapath."))
            else:
                bottom_ports.append((p, w, False, False, 2, "Bidirectional IO port placed on bottom edge."))

        # Place Top Ports
        if top_ports:
            spacing = die_width_um / (len(top_ports) + 1)
            for idx, (p, w, is_clk, cts_req, fanout, reason) in enumerate(top_ports):
                x = (idx + 1) * spacing
                y = die_height_um
                self.ports.append(PlacedPort(p.name, p.direction, w, "top", x, y, "metal4", is_clk, cts_req, fanout, reason))

        # Place Left Ports
        if left_ports:
            spacing = core_height_um / (len(left_ports) + 1)
            for idx, (p, w, is_clk, cts_req, fanout, reason) in enumerate(left_ports):
                x = 0
                y = die_margin_um + (idx + 1) * spacing
                self.ports.append(PlacedPort(p.name, p.direction, w, "left", x, y, "metal3", is_clk, cts_req, fanout, reason))

        # Place Right Ports
        if right_ports:
            spacing = core_height_um / (len(right_ports) + 1)
            for idx, (p, w, is_clk, cts_req, fanout, reason) in enumerate(right_ports):
                x = die_width_um
                y = die_margin_um + (idx + 1) * spacing
                self.ports.append(PlacedPort(p.name, p.direction, w, "right", x, y, "metal3", is_clk, cts_req, fanout, reason))

        # Place Bottom Ports
        if bottom_ports:
            spacing = die_width_um / (len(bottom_ports) + 1)
            for idx, (p, w, is_clk, cts_req, fanout, reason) in enumerate(bottom_ports):
                x = (idx + 1) * spacing
                y = 0
                self.ports.append(PlacedPort(p.name, p.direction, w, "bottom", x, y, "metal4", is_clk, cts_req, fanout, reason))

        return {
            "die": {
                "width_um": die_width_um,
                "height_um": die_height_um,
                "area_um2": die_area_um2,
                "margin_um": die_margin_um
            },
            "core": {
                "x_um": die_margin_um,
                "y_um": die_margin_um,
                "width_um": core_width_um,
                "height_um": core_height_um,
                "area_um2": actual_core_area,
                "utilization_pct": actual_utilization,
                "aspect_ratio": aspect_ratio,
                "num_rows": num_rows,
                "row_height_um": row_h
            },
            "rows": [r.to_dict() for r in self.rows],
            "ports": [p.to_dict() for p in self.ports],
            "macros": self.macros
        }
