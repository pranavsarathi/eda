# Clock Tree Synthesis (CTS) Estimation & Balanced Tree Builder
from typing import Dict, List, Any, Tuple
import math
from eda.technology_model.tech_library import TechnologyModel

class CTSBufferNode:
    def __init__(self, name: str, level: int, x_um: float, y_um: float, cell_type: str = "CLKBUF_X8"):
        self.name = name
        self.level = level
        self.x_um = x_um
        self.y_um = y_um
        self.cell_type = cell_type
        self.children: List[str] = [] # names of child buffers or sink FFs

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "level": self.level,
            "x_um": round(self.x_um, 2),
            "y_um": round(self.y_um, 2),
            "cell_type": self.cell_type,
            "children": self.children
        }

class CTSSynthesizer:
    def __init__(self, placement_data: Dict[str, Any], floorplan_data: Dict[str, Any], tech: TechnologyModel):
        self.placement = placement_data
        self.fp = floorplan_data
        self.tech = tech
        self.buffers: List[CTSBufferNode] = []
        self.tree_segments: List[Dict[str, Any]] = []

    def synthesize(self) -> Dict[str, Any]:
        self.buffers.clear()
        self.tree_segments.clear()

        core = self.fp["core"]
        core_x = core["x_um"]
        core_y = core["y_um"]
        core_w = core["width_um"]
        core_h = core["height_um"]

        # 1. Identify all sequential sink flip-flops
        sinks = [c for c in self.placement.get("cells", []) if c.get("function") in ("DFF", "DFFR", "DFFRE")]
        num_sinks = len(sinks)

        if num_sinks == 0:
            return {
                "clock_sinks": 0,
                "tree_levels": 0,
                "buffer_count": 0,
                "clock_fanout": 0,
                "clock_path_length_um": 0.0,
                "estimated_skew_ps": 0.0,
                "insertion_delay_ns": 0.0,
                "buffers": [],
                "tree_segments": [],
                "explanation": "No sequential clock sinks detected in design; CTS is not required."
            }

        # 2. Determine CTS topology & depth
        # Fanout per buffer: ~ 4 to 8 FFs per leaf buffer
        max_leaf_fanout = 6
        num_leaf_buffers = max(1, int(math.ceil(num_sinks / float(max_leaf_fanout))))

        # Determine tree levels:
        # If <= 6 sinks: 1 level (Root directly drives sinks or 1 buffer)
        # If <= 36 sinks: 2 levels (Root -> Leaf buffers -> Sinks)
        # Else: 3 levels (Root -> Branch buffers -> Leaf buffers -> Sinks)
        if num_leaf_buffers == 1:
            tree_levels = 1
        elif num_leaf_buffers <= 8:
            tree_levels = 2
        else:
            tree_levels = 3

        # Root buffer at top center (near CLK pin)
        clk_port = next((p for p in self.fp.get("ports", []) if p.get("is_clock")), None)
        root_x = clk_port["x_um"] if clk_port else (core_x + core_w / 2.0)
        root_y = core_y + core_h - 2.0

        root_buf = CTSBufferNode("CTS_ROOT_BUF", level=0, x_um=root_x, y_um=root_y, cell_type="CLKBUF_X16")
        self.buffers.append(root_buf)

        # 3. Geometric placement of intermediate branch & leaf buffers
        if tree_levels == 1:
            for s in sinks:
                root_buf.children.append(s["inst_name"])
                self.tree_segments.append({
                    "from_x": root_x, "from_y": root_y,
                    "to_x": s["x_um"], "to_y": s["y_um"],
                    "layer": "metal4"
                })

        elif tree_levels == 2:
            # Root -> Leaf buffers across core columns
            cols = num_leaf_buffers
            col_spacing = core_w / (cols + 1)
            for c_idx in range(cols):
                leaf_x = core_x + (c_idx + 1) * col_spacing
                leaf_y = core_y + core_h / 2.0
                leaf_buf = CTSBufferNode(f"CTS_LEAF_BUF_{c_idx+1}", level=1, x_um=leaf_x, y_um=leaf_y, cell_type="CLKBUF_X4")
                self.buffers.append(leaf_buf)
                root_buf.children.append(leaf_buf.name)

                # Route from root to leaf (Trunk in M5, drop in M4)
                self.tree_segments.append({
                    "from_x": root_x, "from_y": root_y,
                    "to_x": leaf_x, "to_y": leaf_y,
                    "layer": "metal5"
                })

                # Assign nearest sinks to this leaf buffer
                sink_slice = sinks[c_idx * max_leaf_fanout : (c_idx + 1) * max_leaf_fanout]
                for s in sink_slice:
                    leaf_buf.children.append(s["inst_name"])
                    self.tree_segments.append({
                        "from_x": leaf_x, "from_y": leaf_y,
                        "to_x": s["x_um"], "to_y": s["y_um"],
                        "layer": "metal4"
                    })

        else: # 3 levels
            num_branches = max(2, int(math.ceil(math.sqrt(num_leaf_buffers))))
            leafs_per_branch = int(math.ceil(num_leaf_buffers / float(num_branches)))

            branch_spacing = core_w / (num_branches + 1)
            for b_idx in range(num_branches):
                b_x = core_x + (b_idx + 1) * branch_spacing
                b_y = core_y + core_h * 0.75
                branch_buf = CTSBufferNode(f"CTS_BR_{b_idx+1}", level=1, x_um=b_x, y_um=b_y, cell_type="CLKBUF_X8")
                self.buffers.append(branch_buf)
                root_buf.children.append(branch_buf.name)

                self.tree_segments.append({
                    "from_x": root_x, "from_y": root_y,
                    "to_x": b_x, "to_y": b_y,
                    "layer": "metal5"
                })

                # Leaf buffers under this branch
                for l_idx in range(leafs_per_branch):
                    cur_leaf_num = b_idx * leafs_per_branch + l_idx + 1
                    if cur_leaf_num > num_leaf_buffers:
                        break
                    l_x = b_x + (l_idx - leafs_per_branch / 2.0) * (branch_spacing * 0.4)
                    l_y = core_y + core_h * 0.35
                    leaf_buf = CTSBufferNode(f"CTS_LEAF_{cur_leaf_num}", level=2, x_um=l_x, y_um=l_y, cell_type="CLKBUF_X4")
                    self.buffers.append(leaf_buf)
                    branch_buf.children.append(leaf_buf.name)

                    self.tree_segments.append({
                        "from_x": b_x, "from_y": b_y,
                        "to_x": l_x, "to_y": l_y,
                        "layer": "metal4"
                    })

                    # Sinks
                    start_s = (cur_leaf_num - 1) * max_leaf_fanout
                    for s in sinks[start_s : start_s + max_leaf_fanout]:
                        leaf_buf.children.append(s["inst_name"])
                        self.tree_segments.append({
                            "from_x": l_x, "from_y": l_y,
                            "to_x": s["x_um"], "to_y": s["y_um"],
                            "layer": "metal4"
                        })

        # 4. Metrics Calculation
        total_clock_wirelength = sum(
            abs(seg["from_x"] - seg["to_x"]) + abs(seg["from_y"] - seg["to_y"])
            for seg in self.tree_segments
        )

        # Insertion delay = Buffer delays + Wire RC delay
        avg_buf_delay_ps = 55.0 * self.tech.info["scale_factor"]
        wire_rc_delay_ps = total_clock_wirelength * 0.12 * self.tech.info["scale_factor"]
        insertion_delay_ps = (tree_levels * avg_buf_delay_ps) + (wire_rc_delay_ps / max(1, len(self.buffers)))
        insertion_delay_ns = round(insertion_delay_ps / 1000.0, 3)

        # Skew estimate (typical balanced tree achieves ~ 3-5% of insertion delay or 15-40ps)
        estimated_skew_ps = round(max(12.0, min(120.0, insertion_delay_ps * 0.045)), 1)

        return {
            "clock_sinks": num_sinks,
            "tree_levels": tree_levels,
            "buffer_count": len(self.buffers),
            "clock_fanout": num_sinks,
            "clock_path_length_um": round(total_clock_wirelength, 1),
            "estimated_skew_ps": estimated_skew_ps,
            "insertion_delay_ns": insertion_delay_ns,
            "buffers": [b.to_dict() for b in self.buffers],
            "tree_segments": self.tree_segments,
            "explanation": (
                "CTS inserts a balanced buffer tree to distribute the clock signal to all sequential elements "
                "with minimal skew and controlled transition slew. This prevents clock race conditions and setup/hold timing violations."
            )
        }
