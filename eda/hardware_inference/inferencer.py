# RTL Hardware Inference Engine - Strictly Causal & User-RTL Driven
from typing import Dict, List, Any, Optional, Set
from eda.parser.ast_nodes import (
    DesignAST, ModuleNode, PortNode, SignalDeclNode, AssignNode,
    AlwaysNode, IfNode, CaseNode, ProceduralAssignNode, BinaryOpNode,
    UnaryOpNode, TernaryOpNode, IdentifierNode, NumberNode, BitSelectNode,
    ConcatNode
)

class InferredBlock:
    def __init__(self, block_type: str, name: str, width: int = 1, details: Dict[str, Any] = None, rtl_line: int = 1):
        self.block_type = block_type # 'REGISTER', 'ADDER', 'SUBTRACTOR', 'MULTIPLIER', 'MUX', 'COMPARATOR', 'FSM', 'COUNTER', 'MEMORY', 'GATE'
        self.name = name
        self.width = max(1, width)
        self.details = details or {}
        self.rtl_line = rtl_line
        self.inputs = []
        self.outputs = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "block_type": self.block_type,
            "name": self.name,
            "width": self.width,
            "details": self.details,
            "rtl_line": self.rtl_line,
            "inputs": self.inputs,
            "outputs": self.outputs
        }

class InferredFSM:
    def __init__(self, state_reg: str, states: List[str], state_width: int, rtl_line: int = 1):
        self.state_reg = state_reg
        self.states = states
        self.state_width = max(1, state_width)
        self.rtl_line = rtl_line

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state_reg": self.state_reg,
            "states": self.states,
            "state_count": len(self.states),
            "state_width": self.state_width,
            "rtl_line": self.rtl_line
        }

class HardwareInferencer:
    def __init__(self, module: ModuleNode):
        self.module = module
        self.blocks: List[InferredBlock] = []
        self.fsms: List[InferredFSM] = []
        self.clock_domains: Set[str] = set()
        self.reset_domains: Set[str] = set()
        self.signal_widths: Dict[str, int] = {}
        self.param_env: Dict[str, int] = {}
        self.schematic_nodes: List[Dict[str, Any]] = []
        self.schematic_links: List[Dict[str, Any]] = []

        self._eval_parameters()
        self._build_width_map()

    def _eval_const(self, node: Any) -> Optional[int]:
        if not node: return None
        if isinstance(node, NumberNode): return node.value
        if isinstance(node, IdentifierNode): return self.param_env.get(node.name)
        if isinstance(node, BinaryOpNode):
            l = self._eval_const(node.left)
            r = self._eval_const(node.right)
            if l is not None and r is not None:
                if node.op == "+": return l + r
                if node.op == "-": return l - r
                if node.op == "*": return l * r
                if node.op == "/": return l // r if r != 0 else 0
                if node.op == "<<": return l << r
                if node.op == ">>": return l >> r
        return None

    def _eval_parameters(self):
        for p in getattr(self.module, "parameters", []):
            val = self._eval_const(p.value)
            self.param_env[p.name] = val if val is not None else 8

    def _get_node_width(self, msb_node, lsb_node=None) -> int:
        if not msb_node: return 1
        msb = self._eval_const(msb_node)
        lsb = self._eval_const(lsb_node) if lsb_node else 0
        if msb is not None:
            return abs(msb - (lsb or 0)) + 1
        return 1

    def _build_width_map(self):
        for p in self.module.ports:
            w = self._get_node_width(p.width_msb, p.width_lsb)
            self.signal_widths[p.name] = w

        for item in self.module.items:
            if isinstance(item, SignalDeclNode):
                w = self._get_node_width(item.width_msb, item.width_lsb)
                self.signal_widths[item.name] = w

    def extract_ops_from_expr(self, expr: Any, parent_target: str, line: int):
        if not expr: return

        if isinstance(expr, BinaryOpNode):
            # Compute width dynamically from operands and target
            left_w = 1
            right_w = 1
            if isinstance(expr.left, IdentifierNode) and expr.left.name in self.signal_widths:
                left_w = self.signal_widths[expr.left.name]
            if isinstance(expr.right, IdentifierNode) and expr.right.name in self.signal_widths:
                right_w = self.signal_widths[expr.right.name]

            target_w = self.signal_widths.get(parent_target, 1)
            w = max(left_w, right_w, target_w)

            if expr.op == "+":
                self.blocks.append(InferredBlock("ADDER", f"ADD_{parent_target}_L{line}", w, {"op": "+", "target": parent_target}, line))
            elif expr.op == "-":
                self.blocks.append(InferredBlock("SUBTRACTOR", f"SUB_{parent_target}_L{line}", w, {"op": "-", "target": parent_target}, line))
            elif expr.op == "*":
                self.blocks.append(InferredBlock("MULTIPLIER", f"MUL_{parent_target}_L{line}", w, {"op": "*", "target": parent_target}, line))
            elif expr.op in ("==", "!=", "<", "<=", ">", ">="):
                self.blocks.append(InferredBlock("COMPARATOR", f"CMP_{parent_target}_L{line}", w, {"op": expr.op, "target": parent_target}, line))
            elif expr.op in ("&", "|", "^", "~&", "~|", "~^"):
                gate_type = {"&": "AND", "|": "OR", "^": "XOR"}.get(expr.op, "LOGIC_GATE")
                self.blocks.append(InferredBlock("GATE", f"{gate_type}_{parent_target}_L{line}", w, {"gate": gate_type, "target": parent_target}, line))

            self.extract_ops_from_expr(expr.left, parent_target, line)
            self.extract_ops_from_expr(expr.right, parent_target, line)

        elif isinstance(expr, TernaryOpNode):
            w = max(self.signal_widths.get(parent_target, 1), 1)
            self.blocks.append(InferredBlock("MUX", f"MUX2_{parent_target}_L{line}", w, {"inputs": 2, "target": parent_target}, line))
            self.extract_ops_from_expr(expr.condition, parent_target, line)
            self.extract_ops_from_expr(expr.true_expr, parent_target, line)
            self.extract_ops_from_expr(expr.false_expr, parent_target, line)

        elif isinstance(expr, UnaryOpNode):
            if expr.op in ("~", "!"):
                w = max(self.signal_widths.get(parent_target, 1), 1)
                self.blocks.append(InferredBlock("GATE", f"INV_{parent_target}_L{line}", w, {"gate": "NOT", "target": parent_target}, line))
            self.extract_ops_from_expr(expr.expr, parent_target, line)

    def scan_statement(self, stmt: Any, is_sequential: bool, clock_sig: Optional[str], reset_sig: Optional[str]):
        if not stmt: return

        if isinstance(stmt, ProceduralAssignNode):
            tgt_name = getattr(stmt.lhs, "name", "")
            if isinstance(stmt.lhs, BitSelectNode):
                tgt_name = getattr(stmt.lhs.target, "name", "")

            w = self.signal_widths.get(tgt_name, 1)

            if is_sequential and tgt_name:
                # Check if counter: q <= q + 1
                is_counter = False
                if isinstance(stmt.rhs, BinaryOpNode) and stmt.rhs.op in ("+", "-"):
                    l_name = getattr(stmt.rhs.left, "name", "")
                    r_name = getattr(stmt.rhs.right, "name", "")
                    if l_name == tgt_name or r_name == tgt_name:
                        is_counter = True
                        self.blocks.append(InferredBlock(
                            "COUNTER",
                            f"CTR_{tgt_name}_L{stmt.line}",
                            w,
                            {
                                "direction": "UP" if stmt.rhs.op == "+" else "DOWN",
                                "clock": clock_sig,
                                "reset": reset_sig,
                                "target": tgt_name
                            },
                            stmt.line
                        ))

                if not is_counter:
                    self.blocks.append(InferredBlock(
                        "REGISTER",
                        f"REG_{tgt_name}_L{stmt.line}",
                        w,
                        {
                            "clock": clock_sig,
                            "reset": reset_sig,
                            "has_reset": reset_sig is not None,
                            "target": tgt_name
                        },
                        stmt.line
                    ))

            self.extract_ops_from_expr(stmt.rhs, tgt_name, stmt.line)

        elif isinstance(stmt, IfNode):
            if isinstance(stmt.condition, BinaryOpNode):
                self.extract_ops_from_expr(stmt.condition, "cond", stmt.line)
            self.scan_statement(stmt.then_branch, is_sequential, clock_sig, reset_sig)
            if stmt.else_branch:
                self.scan_statement(stmt.else_branch, is_sequential, clock_sig, reset_sig)

        elif isinstance(stmt, CaseNode):
            case_var = getattr(stmt.expr, "name", "")
            state_vals = []
            for ci in stmt.items:
                if not ci.is_default:
                    for c in ci.conditions:
                        s_name = getattr(c, "name", None)
                        if s_name: state_vals.append(s_name)
                        elif hasattr(c, "raw"): state_vals.append(c.raw)

            if len(state_vals) >= 2 and ("state" in case_var.lower() or "fsm" in case_var.lower() or len(state_vals) >= 3):
                w = self.signal_widths.get(case_var, 3)
                existing_fsm = next((f for f in self.fsms if f.state_reg == case_var), None)
                if existing_fsm:
                    for sv in state_vals:
                        if sv not in existing_fsm.states:
                            existing_fsm.states.append(sv)
                    for b in self.blocks:
                        if b.block_type == "FSM" and b.details.get("state_reg") == case_var:
                            b.details["states"] = existing_fsm.states
                            b.details["state_count"] = len(existing_fsm.states)
                else:
                    fsm = InferredFSM(case_var, list(state_vals), w, stmt.line)
                    self.fsms.append(fsm)
                    self.blocks.append(InferredBlock(
                        "FSM",
                        f"FSM_{case_var}",
                        w,
                        {"state_reg": case_var, "states": list(state_vals), "state_count": len(state_vals), "state_width": w},
                        stmt.line
                    ))
            else:
                w = self.signal_widths.get(case_var, 1)
                self.blocks.append(InferredBlock(
                    "MUX",
                    f"MUX{len(stmt.items)}_L{stmt.line}",
                    w,
                    {"inputs": len(stmt.items), "selector": case_var},
                    stmt.line
                ))

            for ci in stmt.items:
                self.scan_statement(ci.body, is_sequential, clock_sig, reset_sig)

        elif hasattr(stmt, "statements"):
            for s in stmt.statements:
                self.scan_statement(s, is_sequential, clock_sig, reset_sig)

    def infer(self) -> Dict[str, Any]:
        self.blocks.clear()
        self.fsms.clear()
        self.clock_domains.clear()
        self.reset_domains.clear()

        # Check for memory arrays
        for item in self.module.items:
            if isinstance(item, SignalDeclNode) and item.array_size:
                w = self.signal_widths.get(item.name, 8)
                depth = self._eval_const(item.array_size) or 16
                self.blocks.append(InferredBlock(
                    "MEMORY",
                    f"RAM_{item.name}_L{item.line}",
                    w,
                    {"depth": depth, "words": depth, "data_width": w},
                    item.line
                ))

        # Continuous assigns
        for item in self.module.items:
            if isinstance(item, AssignNode):
                tgt_name = getattr(item.lhs, "name", "wire")
                self.extract_ops_from_expr(item.rhs, tgt_name, item.line)

        # Procedural blocks
        detected_reset_type = "NONE"
        detected_reset_polarity = "ACTIVE_HIGH"

        for item in self.module.items:
            if isinstance(item, AlwaysNode):
                is_seq = False
                clk = None
                rst = None
                cur_rst_type = None
                cur_rst_pol = "ACTIVE_HIGH"

                for s in item.sensitivity:
                    if s.edge in ("posedge", "negedge"):
                        is_seq = True
                        s_lower = s.signal.lower()
                        if "clk" in s_lower or "clock" in s_lower:
                            clk = s.signal
                            self.clock_domains.add(clk)
                        elif "rst" in s_lower or "reset" in s_lower:
                            rst = s.signal
                            cur_rst_type = "ASYNCHRONOUS"
                            cur_rst_pol = "ACTIVE_LOW" if s.edge == "negedge" else "ACTIVE_HIGH"
                            self.reset_domains.add(rst)
                        else:
                            clk = s.signal
                            self.clock_domains.add(clk)

                # Check for synchronous reset if not in sensitivity
                if is_seq and not rst:
                    top_stmt = item.body
                    if hasattr(top_stmt, "statements") and len(top_stmt.statements) > 0:
                        top_stmt = top_stmt.statements[0]
                    if isinstance(top_stmt, IfNode):
                        cond = top_stmt.condition
                        def get_cond_sigs(node):
                            res = set()
                            if not node: return res
                            if isinstance(node, IdentifierNode): res.add(node.name)
                            elif isinstance(node, UnaryOpNode): res |= get_cond_sigs(node.expr)
                            elif isinstance(node, BinaryOpNode): res |= get_cond_sigs(node.left) | get_cond_sigs(node.right)
                            return res
                        for cs in get_cond_sigs(cond):
                            cs_lower = cs.lower()
                            if "rst" in cs_lower or "reset" in cs_lower or any(p.name == cs for p in self.module.ports if "rst" in p.name.lower() or "reset" in p.name.lower()):
                                rst = cs
                                cur_rst_type = "SYNCHRONOUS"
                                if isinstance(cond, UnaryOpNode) and cond.op in ("!", "~"):
                                    cur_rst_pol = "ACTIVE_LOW"
                                elif isinstance(cond, BinaryOpNode) and cond.op in ("==", "==="):
                                    if isinstance(cond.right, NumberNode) and cond.right.value == 0:
                                        cur_rst_pol = "ACTIVE_LOW"
                                    else:
                                        cur_rst_pol = "ACTIVE_HIGH"
                                else:
                                    cur_rst_pol = "ACTIVE_HIGH"
                                self.reset_domains.add(rst)
                                break

                if cur_rst_type:
                    detected_reset_type = cur_rst_type
                    detected_reset_polarity = cur_rst_pol

                self.scan_statement(item.body, is_seq, clk, rst)

        # Deduplicate and consolidate blocks
        # In sequential logic, assignments to a target variable all map to ONE physical register or counter
        seq_by_target = {}
        non_seq_blocks = []

        for b in self.blocks:
            if b.block_type in ("REGISTER", "COUNTER"):
                tgt = b.details.get("target") or b.name
                if tgt not in seq_by_target:
                    seq_by_target[tgt] = b
                else:
                    existing = seq_by_target[tgt]
                    if b.block_type == "COUNTER":
                        seq_by_target[tgt] = b
                    elif existing.block_type != "COUNTER":
                        if b.details.get("has_reset"):
                            existing.details["has_reset"] = True
                            existing.details["reset"] = b.details.get("reset")
            else:
                non_seq_blocks.append(b)

        unique_non_seq = []
        seen = set()
        for b in non_seq_blocks:
            key = (b.block_type, b.name, b.rtl_line)
            if key not in seen:
                seen.add(key)
                unique_non_seq.append(b)

        self.blocks = list(seq_by_target.values()) + unique_non_seq

        # Build Schematic graph nodes and links for UI visualization
        self.schematic_nodes.clear()
        self.schematic_links.clear()

        for p in self.module.ports:
            node_id = f"port_{p.name}"
            self.schematic_nodes.append({
                "id": node_id,
                "label": p.name,
                "type": "PORT",
                "direction": p.direction,
                "width": self.signal_widths.get(p.name, 1),
                "line": p.line
            })

        for idx, b in enumerate(self.blocks):
            node_id = f"blk_{idx}_{b.name}"
            self.schematic_nodes.append({
                "id": node_id,
                "label": b.name,
                "type": b.block_type,
                "width": b.width,
                "details": b.details,
                "line": b.rtl_line
            })

        # Summary counts - STRICTLY SUMMED FROM INFERRED BLOCKS
        reg_bits = sum(b.width for b in self.blocks if b.block_type in ("REGISTER", "COUNTER"))
        adder_count = sum(1 for b in self.blocks if b.block_type in ("ADDER", "SUBTRACTOR"))
        mul_count = sum(1 for b in self.blocks if b.block_type == "MULTIPLIER")
        mux_count = sum(1 for b in self.blocks if b.block_type == "MUX")
        cmp_count = sum(1 for b in self.blocks if b.block_type == "COMPARATOR")
        gate_count = sum(1 for b in self.blocks if b.block_type == "GATE")
        fsm_count = len(self.fsms)
        mem_count = sum(1 for b in self.blocks if b.block_type == "MEMORY")

        return {
            "blocks": [b.to_dict() for b in self.blocks],
            "fsms": [f.to_dict() for f in self.fsms],
            "clock_domains": list(self.clock_domains),
            "reset_domains": list(self.reset_domains),
            "reset_type": detected_reset_type.lower() if detected_reset_type != "NONE" else "none",
            "reset_polarity": detected_reset_polarity.lower(),
            "register_bits": reg_bits,
            "adders": adder_count,
            "multipliers": mul_count,
            "multiplexers": mux_count,
            "comparators": cmp_count,
            "logic_gates": gate_count,
            "memories": mem_count,
            "fsms_count": fsm_count,
            "schematic": {
                "nodes": self.schematic_nodes,
                "links": self.schematic_links
            }
        }
