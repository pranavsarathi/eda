# Configurable Technology Library and Standard Cell Physical Abstraction
from typing import Dict, Any, Optional

class StandardCell:
    def __init__(self, name: str, function: str, area_um2: float, width_um: float, height_um: float,
                 pin_cap_ff: float, intrinsic_delay_ps: float, drive_res_kohm: float,
                 leakage_nw: float, dynamic_energy_fj: float, inputs: int = 1):
        self.name = name
        self.function = function # 'INV', 'NAND2', 'NOR2', 'AND2', 'OR2', 'XOR2', 'MUX2', 'DFF', 'DFFR', 'FA', 'HA', 'BUF', 'CLKBUF', 'FILL'
        self.area_um2 = area_um2
        self.width_um = width_um
        self.height_um = height_um
        self.pin_cap_ff = pin_cap_ff
        self.intrinsic_delay_ps = intrinsic_delay_ps
        self.drive_res_kohm = drive_res_kohm
        self.leakage_nw = leakage_nw
        self.dynamic_energy_fj = dynamic_energy_fj
        self.inputs = inputs

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "function": self.function,
            "area_um2": self.area_um2,
            "width_um": self.width_um,
            "height_um": self.height_um,
            "pin_cap_ff": self.pin_cap_ff,
            "intrinsic_delay_ps": self.intrinsic_delay_ps,
            "drive_res_kohm": self.drive_res_kohm,
            "leakage_nw": self.leakage_nw,
            "dynamic_energy_fj": self.dynamic_energy_fj
        }

class TechnologyModel:
    TECH_NODES = {
        "180nm": {
            "name": "Generic 180nm CMOS",
            "scale_factor": 1.45,
            "vdd": 1.8,
            "row_height_um": 5.04,
            "site_width_um": 0.56,
            "metal_layers": 6,
            "wire_res_ohm_per_um": 0.08,
            "wire_cap_ff_per_um": 0.18,
            "nand2_area_um2": 15.0,
            "dff_area_um2": 65.0,
            "typical_fmax_mhz": 200
        },
        "130nm": {
            "name": "Generic 130nm CMOS (SkyWater-like)",
            "scale_factor": 1.0,
            "vdd": 1.2,
            "row_height_um": 2.72,
            "site_width_um": 0.46,
            "metal_layers": 6,
            "wire_res_ohm_per_um": 0.12,
            "wire_cap_ff_per_um": 0.15,
            "nand2_area_um2": 7.4,
            "dff_area_um2": 32.6,
            "typical_fmax_mhz": 350
        },
        "65nm": {
            "name": "Generic 65nm Low-Power CMOS",
            "scale_factor": 0.52,
            "vdd": 1.0,
            "row_height_um": 1.4,
            "site_width_um": 0.2,
            "metal_layers": 7,
            "wire_res_ohm_per_um": 0.25,
            "wire_cap_ff_per_um": 0.14,
            "nand2_area_um2": 1.9,
            "dff_area_um2": 9.2,
            "typical_fmax_mhz": 600
        },
        "45nm": {
            "name": "Generic 45nm Planar High-K Metal Gate",
            "scale_factor": 0.35,
            "vdd": 0.9,
            "row_height_um": 0.96,
            "site_width_um": 0.14,
            "metal_layers": 8,
            "wire_res_ohm_per_um": 0.38,
            "wire_cap_ff_per_um": 0.13,
            "nand2_area_um2": 0.95,
            "dff_area_um2": 4.6,
            "typical_fmax_mhz": 900
        },
        "28nm": {
            "name": "Generic 28nm FD-SOI / High-Performance",
            "scale_factor": 0.22,
            "vdd": 0.8,
            "row_height_um": 0.6,
            "site_width_um": 0.1,
            "metal_layers": 8,
            "wire_res_ohm_per_um": 0.55,
            "wire_cap_ff_per_um": 0.12,
            "nand2_area_um2": 0.42,
            "dff_area_um2": 2.1,
            "typical_fmax_mhz": 1200
        },
        "7nm": {
            "name": "Generic 7nm FinFET",
            "scale_factor": 0.08,
            "vdd": 0.7,
            "row_height_um": 0.24,
            "site_width_um": 0.04,
            "metal_layers": 10,
            "wire_res_ohm_per_um": 1.20,
            "wire_cap_ff_per_um": 0.11,
            "nand2_area_um2": 0.065,
            "dff_area_um2": 0.38,
            "typical_fmax_mhz": 2500
        }
    }

    def __init__(self, node: str = "130nm", core_utilization: float = 0.70,
                 aspect_ratio: float = 1.0, clock_target_mhz: float = 100.0,
                 routing_layers: int = 6):
        self.node = node if node in self.TECH_NODES else "130nm"
        self.core_utilization = max(0.2, min(0.95, core_utilization))
        self.aspect_ratio = max(0.2, min(5.0, aspect_ratio))
        self.clock_target_mhz = clock_target_mhz
        self.routing_layers = routing_layers

        self.info = self.TECH_NODES[self.node]
        self.cells = self._build_cell_library()

    def _build_cell_library(self) -> Dict[str, StandardCell]:
        s = self.info["scale_factor"]
        h = self.info["row_height_um"]

        # Base 130nm sizes scaled by node factor
        def cell(name, fn, w_base, delay_base, r_base, cap_base, leak_base, dyn_base, inps=1):
            w = max(self.info["site_width_um"], round(w_base * s, 2))
            area = round(w * h, 3)
            return StandardCell(
                name=name,
                function=fn,
                area_um2=area,
                width_um=w,
                height_um=h,
                pin_cap_ff=round(cap_base * s, 2),
                intrinsic_delay_ps=round(delay_base * (0.6 + 0.4 * s), 1),
                drive_res_kohm=round(r_base / max(0.1, s), 2),
                leakage_nw=round(leak_base * (1.0 / max(0.1, s * 0.8)), 3),
                dynamic_energy_fj=round(dyn_base * s, 3),
                inputs=inps
            )

        return {
            "INV_X1": cell("INV_X1", "INV", 0.92, 28, 4.2, 1.8, 0.4, 0.5, 1),
            "BUF_X1": cell("BUF_X1", "BUF", 1.38, 45, 3.5, 2.0, 0.7, 0.9, 1),
            "CLKBUF_X4": cell("CLKBUF_X4", "CLKBUF", 2.76, 52, 1.2, 3.5, 1.8, 2.4, 1),
            "CLKBUF_X8": cell("CLKBUF_X8", "CLKBUF", 4.14, 58, 0.7, 5.0, 3.2, 4.2, 1),
            "CLKBUF_X16": cell("CLKBUF_X16", "CLKBUF", 6.90, 65, 0.4, 8.5, 6.0, 7.8, 1),
            "NAND2_X1": cell("NAND2_X1", "NAND2", 1.38, 35, 3.8, 2.2, 0.6, 0.8, 2),
            "NOR2_X1": cell("NOR2_X1", "NOR2", 1.38, 42, 4.5, 2.4, 0.8, 0.9, 2),
            "AND2_X1": cell("AND2_X1", "AND2", 1.84, 48, 3.6, 2.5, 0.9, 1.2, 2),
            "OR2_X1": cell("OR2_X1", "OR2", 1.84, 54, 3.9, 2.6, 1.0, 1.3, 2),
            "XOR2_X1": cell("XOR2_X1", "XOR2", 2.76, 68, 4.8, 3.2, 1.5, 1.9, 2),
            "MUX2_X1": cell("MUX2_X1", "MUX2", 3.22, 75, 4.0, 3.6, 1.8, 2.2, 3),
            "FA_X1": cell("FA_X1", "FA", 6.44, 125, 3.5, 6.8, 4.2, 5.5, 3),
            "HA_X1": cell("HA_X1", "HA", 3.68, 85, 3.8, 4.2, 2.4, 3.1, 2),
            "DFFR_X1": cell("DFFR_X1", "DFFR", 5.52, 95, 3.2, 4.5, 3.6, 4.8, 3),
            "DFFRE_X1": cell("DFFRE_X1", "DFFRE", 6.90, 110, 3.1, 5.2, 4.5, 5.8, 4),
            "FILL1": cell("FILL1", "FILL", 0.46, 0, 0, 0, 0.05, 0, 0),
            "FILL2": cell("FILL2", "FILL", 0.92, 0, 0, 0, 0.08, 0, 0),
            "FILL4": cell("FILL4", "FILL", 1.84, 0, 0, 0, 0.12, 0, 0),
            "FILL8": cell("FILL8", "FILL", 3.68, 0, 0, 0, 0.20, 0, 0),
            "FILL16": cell("FILL16", "FILL", 7.36, 0, 0, 0, 0.35, 0, 0)
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node": self.node,
            "name": self.info["name"],
            "vdd": self.info["vdd"],
            "core_utilization": self.core_utilization,
            "aspect_ratio": self.aspect_ratio,
            "clock_target_mhz": self.clock_target_mhz,
            "routing_layers": self.routing_layers,
            "row_height_um": self.info["row_height_um"],
            "site_width_um": self.info["site_width_um"],
            "wire_res_ohm_per_um": self.info["wire_res_ohm_per_um"],
            "wire_cap_ff_per_um": self.info["wire_cap_ff_per_um"],
            "nand2_area_um2": self.info["nand2_area_um2"],
            "dff_area_um2": self.info["dff_area_um2"]
        }
