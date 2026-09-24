# Multi-Layer Rectilinear Router & Power Network Estimator
from typing import Dict, List, Any, Tuple
import math
from eda.technology_model.tech_library import TechnologyModel
from eda.routing_engine.congestion import CongestionEstimator

class RouteSegment:
    def __init__(self, x1: float, y1: float, x2: float, y2: float, layer: str, net_name: str, is_critical: bool = False):
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.layer = layer
        self.net_name = net_name
        self.is_critical = is_critical

    def to_dict(self) -> Dict[str, Any]:
        return {
            "x1": round(self.x1, 2),
            "y1": round(self.y1, 2),
            "x2": round(self.x2, 2),
            "y2": round(self.y2, 2),
            "layer": self.layer,
            "net_name": self.net_name,
            "is_critical": self.is_critical
        }

class EstimatedRouter:
    def __init__(self, placement_data: Dict[str, Any], floorplan_data: Dict[str, Any], tech: TechnologyModel):
        self.placement = placement_data
        self.fp = floorplan_data
        self.tech = tech
        self.route_segments: List[RouteSegment] = []
        self.flightlines: List[Dict[str, Any]] = [] # Before routing ratsnest
        self.power_mesh: List[Dict[str, Any]] = []
        self.vias: Dict[str, int] = {"V12": 0, "V23": 0, "V34": 0, "V45": 0, "V56": 0}

    def route(self) -> Dict[str, Any]:
        self.route_segments.clear()
        self.flightlines.clear()
        self.power_mesh.clear()
        self.vias = {"V12": 0, "V23": 0, "V34": 0, "V45": 0, "V56": 0}

        core = self.fp["core"]
        die = self.fp["die"]
        core_x = core["x_um"]
        core_y = core["y_um"]
        core_w = core["width_um"]
        core_h = core["height_um"]

        cells = self.placement.get("cells", [])
        ports = self.fp.get("ports", [])

        # 1. Congestion Grid Initializer
        congestion = CongestionEstimator(core_x, core_y, core_w, core_h, grid_size=12)

        # 2. Build Nets and Connectivity
        # Connect IO input ports to nearest logic cells
        # Connect consecutive logic cells in pipeline
        # Connect outputs to logic cells
        net_idx = 0
        total_nets = 0
        critical_nets_count = 0
        total_wirelength_um = 0.0

        # Input Port -> First logic cells
        input_ports = [p for p in ports if p["direction"] == "input" and not p.get("is_clock")]
        for p in input_ports:
            net_idx += 1
            total_nets += 1
            net_name = f"net_{p['name']}"
            p_x, p_y = p["x_um"], p["y_um"]

            # Connect to nearest cells
            if cells:
                target_cell = min(cells, key=lambda c: abs(c["x_um"] - p_x) + abs(c["y_um"] - p_y))
                c_x = target_cell["x_um"] + target_cell["width_um"] / 2.0
                c_y = target_cell["y_um"] + target_cell["height_um"] / 2.0

                # Flightline (ratsnest)
                self.flightlines.append({
                    "from_x": p_x, "from_y": p_y, "to_x": c_x, "to_y": c_y,
                    "net_name": net_name
                })

                # Rectilinear Route: Horizontal on M3, Vertical on M2/M4
                corner_x = c_x
                corner_y = p_y
                self.route_segments.append(RouteSegment(p_x, p_y, corner_x, corner_y, "metal3", net_name))
                self.route_segments.append(RouteSegment(corner_x, corner_y, c_x, c_y, "metal2", net_name))
                self.vias["V23"] += 1

                congestion.add_route_demand(p_x, p_y, c_x, c_y)
                total_wirelength_um += abs(p_x - corner_x) + abs(corner_y - c_y)

        # Cell-to-Cell Interconnects
        for i in range(len(cells) - 1):
            net_idx += 1
            total_nets += 1
            c1 = cells[i]
            c2 = cells[i + 1]
            x1 = c1["x_um"] + c1["width_um"]
            y1 = c1["y_um"] + c1["height_um"] / 2.0
            x2 = c2["x_um"]
            y2 = c2["y_um"] + c2["height_um"] / 2.0

            net_name = f"net_U{i}_to_U{i+1}"
            is_crit = (i < 8) # first stages along critical path
            if is_crit:
                critical_nets_count += 1

            # Flightline
            self.flightlines.append({
                "from_x": x1, "from_y": y1, "to_x": x2, "to_y": y2,
                "net_name": net_name, "is_critical": is_crit
            })

            # Rectilinear Manhattan Route
            # If same row, route horizontal directly on M1/M3
            if abs(y1 - y2) < 0.1:
                self.route_segments.append(RouteSegment(x1, y1, x2, y2, "metal3", net_name, is_crit))
                total_wirelength_um += abs(x2 - x1)
            else:
                mid_x = (x1 + x2) / 2.0
                # Segment 1: M3 horizontal
                self.route_segments.append(RouteSegment(x1, y1, mid_x, y1, "metal3", net_name, is_crit))
                # Segment 2: M2 or M4 vertical
                v_layer = "metal4" if is_crit else "metal2"
                self.route_segments.append(RouteSegment(mid_x, y1, mid_x, y2, v_layer, net_name, is_crit))
                # Segment 3: M3 horizontal
                self.route_segments.append(RouteSegment(mid_x, y2, x2, y2, "metal3", net_name, is_crit))
                self.vias["V23"] += 2
                if is_crit:
                    self.vias["V34"] += 2

                total_wirelength_um += abs(x1 - mid_x) + abs(y1 - y2) + abs(mid_x - x2)

            congestion.add_route_demand(x1, y1, x2, y2)

        # Logic Cells -> Output Ports
        output_ports = [p for p in ports if p["direction"] == "output"]
        for p in output_ports:
            net_idx += 1
            total_nets += 1
            net_name = f"net_{p['name']}"
            p_x, p_y = p["x_um"], p["y_um"]

            if cells:
                driver_cell = min(cells, key=lambda c: abs(c["x_um"] - p_x) + abs(c["y_um"] - p_y))
                c_x = driver_cell["x_um"] + driver_cell["width_um"]
                c_y = driver_cell["y_um"] + driver_cell["height_um"] / 2.0

                self.flightlines.append({
                    "from_x": c_x, "from_y": c_y, "to_x": p_x, "to_y": p_y,
                    "net_name": net_name
                })

                corner_x = c_x + 5.0
                self.route_segments.append(RouteSegment(c_x, c_y, corner_x, c_y, "metal3", net_name))
                self.route_segments.append(RouteSegment(corner_x, c_y, corner_x, p_y, "metal4", net_name))
                self.route_segments.append(RouteSegment(corner_x, p_y, p_x, p_y, "metal3", net_name))
                self.vias["V34"] += 2
                congestion.add_route_demand(c_x, c_y, p_x, p_y)
                total_wirelength_um += abs(c_x - corner_x) + abs(c_y - p_y) + abs(corner_x - p_x)

        # 3. Power Distribution Network (PDN)
        # Power Core Ring (VDD outer, VSS inner around core boundary on M5/M6)
        ring_offset = 2.0
        # VDD Ring (Red)
        self.power_mesh.append({
            "type": "RING", "net": "VDD",
            "x1": core_x - ring_offset, "y1": core_y - ring_offset,
            "x2": core_x + core_w + ring_offset, "y2": core_y + core_h + ring_offset,
            "layer": "metal6", "width_um": 2.5
        })
        # VSS Ring (Blue)
        self.power_mesh.append({
            "type": "RING", "net": "VSS",
            "x1": core_x - ring_offset * 2.0, "y1": core_y - ring_offset * 2.0,
            "x2": core_x + core_w + ring_offset * 2.0, "y2": core_y + core_h + ring_offset * 2.0,
            "layer": "metal6", "width_um": 2.5
        })

        # Upper Metal Power Stripes (M6 Vertical stripes across core)
        num_stripes = max(2, int(core_w / 25.0))
        stripe_spacing = core_w / (num_stripes + 1)
        for s_idx in range(num_stripes):
            sx = core_x + (s_idx + 1) * stripe_spacing
            net = "VDD" if (s_idx % 2 == 0) else "VSS"
            self.power_mesh.append({
                "type": "STRIPE", "net": net,
                "x1": sx, "y1": core_y, "x2": sx, "y2": core_y + core_h,
                "layer": "metal6", "width_um": 1.8
            })
            self.vias["V56"] += 4

        # Follow-pin Power Rails along standard cell rows (M1 horizontal rails)
        rows = self.fp.get("rows", [])
        for r in rows:
            ry = r["y_um"]
            # Bottom rail of row
            self.power_mesh.append({
                "type": "RAIL", "net": "VSS" if r["orientation"] == "R0" else "VDD",
                "x1": core_x, "y1": ry, "x2": core_x + core_w, "y2": ry,
                "layer": "metal1", "width_um": 0.48
            })
            # Top rail of row
            self.power_mesh.append({
                "type": "RAIL", "net": "VDD" if r["orientation"] == "R0" else "VSS",
                "x1": core_x, "y1": ry + r["height_um"], "x2": core_x + core_w, "y2": ry + r["height_um"],
                "layer": "metal1", "width_um": 0.48
            })
            self.vias["V12"] += 6

        # 4. Congestion metrics
        cong_metrics = congestion.calculate_metrics()

        return {
            "status": "ESTIMATED_ROUTED",
            "estimated_nets": total_nets,
            "estimated_routed": total_nets,
            "critical_nets": critical_nets_count,
            "estimated_total_wirelength_um": round(total_wirelength_um, 1),
            "estimated_drc_risk": cong_metrics["estimated_drc_risk"],
            "average_congestion_pct": cong_metrics["average_congestion_pct"],
            "max_tile_congestion_pct": cong_metrics["max_tile_congestion_pct"],
            "vias_breakdown": self.vias,
            "total_vias_count": sum(self.vias.values()),
            "route_segments": [s.to_dict() for s in self.route_segments],
            "flightlines": self.flightlines,
            "power_mesh": self.power_mesh,
            "congestion_grid": cong_metrics
        }
