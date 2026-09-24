# Real Cycle-Accurate Verilog Simulator & User Testbench Execution Engine
import re
import time
from typing import Dict, List, Any, Optional, Tuple

from eda.parser.ast_nodes import (
    DesignAST, ModuleNode, PortNode, SignalDeclNode, AssignNode,
    AlwaysNode, IfNode, CaseNode, ProceduralAssignNode, BinaryOpNode,
    UnaryOpNode, TernaryOpNode, IdentifierNode, NumberNode, BitSelectNode,
    ConcatNode, ReplicateNode, InitialNode, DelayNode, SystemTaskNode,
    AssertNode, InstanceNode
)

class SimValue:
    def __init__(self, value: int = 0, width: int = 1, is_x: bool = False):
        self.width = max(1, width)
        self.mask = (1 << self.width) - 1
        self.is_x = is_x
        self.value = (value & self.mask) if not is_x else 0

    def get_int(self) -> int:
        return self.value if not self.is_x else 0

    def __repr__(self):
        if self.is_x: return f"x[{self.width}]"
        return f"{self.value}'d({self.width}b)"

class RTLSimulator:
    def __init__(self, module: ModuleNode, param_overrides: Dict[str, int] = None):
        self.module = module
        self.signals: Dict[str, SimValue] = {}
        self.signal_widths: Dict[str, int] = {}
        self.ports: Dict[str, str] = {} # name -> direction
        self.clock_signals: List[str] = []
        self.reset_signals: List[str] = []
        self.param_env: Dict[str, int] = {}
        self.time_step = 0
        self.memory_arrays: Dict[str, List[int]] = {}
        self.nba_queue: List[Tuple[str, SimValue]] = []

        self._eval_parameters(param_overrides or {})
        self._initialize_signals()

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

    def _eval_parameters(self, overrides: Dict[str, int]):
        for p in getattr(self.module, "parameters", []):
            val = self._eval_const(p.value)
            self.param_env[p.name] = val if val is not None else 8
        self.param_env.update(overrides)

    def _get_node_width(self, msb_node, lsb_node=None) -> int:
        if not msb_node: return 1
        msb = self._eval_const(msb_node)
        lsb = self._eval_const(lsb_node) if lsb_node else 0
        if msb is not None:
            return abs(msb - (lsb or 0)) + 1
        return 1

    def _initialize_signals(self):
        for p in self.module.ports:
            w = self._get_node_width(p.width_msb, p.width_lsb)
            self.ports[p.name] = p.direction
            self.signal_widths[p.name] = w
            self.signals[p.name] = SimValue(0, w, is_x=False)

            p_lower = p.name.lower()
            if "clk" in p_lower or "clock" in p_lower:
                self.clock_signals.append(p.name)
            elif "rst" in p_lower or "reset" in p_lower:
                self.reset_signals.append(p.name)

        for item in self.module.items:
            if isinstance(item, SignalDeclNode):
                w = self._get_node_width(item.width_msb, item.width_lsb)
                self.signal_widths[item.name] = w
                self.signals[item.name] = SimValue(0, w, is_x=False)

                if item.array_size:
                    depth = self._eval_const(item.array_size) or 16
                    self.memory_arrays[item.name] = [0] * (depth + 1)

    def set_input(self, name: str, value: int):
        if name in self.signals:
            w = self.signal_widths.get(name, 1)
            self.signals[name] = SimValue(value, w, is_x=False)

    def get_signal(self, name: str) -> int:
        return self.signals[name].get_int() if name in self.signals else 0

    def eval_expr(self, node: Any, local_env: Dict[str, SimValue] = None) -> SimValue:
        if not node: return SimValue(0, 1)
        env = local_env or self.signals

        if isinstance(node, NumberNode):
            w = node.width or max(1, node.value.bit_length())
            return SimValue(node.value, w)

        if isinstance(node, IdentifierNode):
            name = node.name
            if name in env:
                return env[name]
            if name in self.param_env:
                v = self.param_env[name]
                return SimValue(v, max(1, v.bit_length()))
            return SimValue(0, 1)

        if isinstance(node, BitSelectNode):
            base = self.eval_expr(node.target, env)
            msb_val = self.eval_expr(node.msb, env).get_int()
            if node.lsb:
                lsb_val = self.eval_expr(node.lsb, env).get_int()
                start = min(msb_val, lsb_val)
                end = max(msb_val, lsb_val)
                w = end - start + 1
                slice_val = (base.get_int() >> start) & ((1 << w) - 1)
                return SimValue(slice_val, w)
            else:
                bit_val = (base.get_int() >> msb_val) & 1
                return SimValue(bit_val, 1)

        if isinstance(node, UnaryOpNode):
            sub = self.eval_expr(node.expr, env)
            val, w = sub.get_int(), sub.width
            if node.op == "~": return SimValue(~val & sub.mask, w)
            if node.op == "!": return SimValue(1 if val == 0 else 0, 1)
            if node.op == "-": return SimValue(-val, w)
            if node.op == "+": return SimValue(val, w)
            if node.op == "&": return SimValue(1 if val == sub.mask else 0, 1)
            if node.op == "|": return SimValue(1 if val != 0 else 0, 1)
            if node.op == "^": return SimValue(bin(val).count("1") % 2, 1)

        if isinstance(node, BinaryOpNode):
            l = self.eval_expr(node.left, env)
            r = self.eval_expr(node.right, env)
            lv, rv = l.get_int(), r.get_int()
            w = max(l.width, r.width)

            if node.op == "+": return SimValue(lv + rv, w)
            if node.op == "-": return SimValue(lv - rv, w)
            if node.op == "*": return SimValue(lv * rv, l.width + r.width)
            if node.op in ("/", "%"):
                if rv == 0: return SimValue(0, w)
                return SimValue(lv // rv if node.op == "/" else lv % rv, w)
            if node.op == "&": return SimValue(lv & rv, w)
            if node.op == "|": return SimValue(lv | rv, w)
            if node.op == "^": return SimValue(lv ^ rv, w)
            if node.op in ("==", "==="): return SimValue(1 if lv == rv else 0, 1)
            if node.op in ("!=", "!=="): return SimValue(1 if lv != rv else 0, 1)
            if node.op == "<": return SimValue(1 if lv < rv else 0, 1)
            if node.op == "<=": return SimValue(1 if lv <= rv else 0, 1)
            if node.op == ">": return SimValue(1 if lv > rv else 0, 1)
            if node.op == ">=": return SimValue(1 if lv >= rv else 0, 1)
            if node.op == "&&": return SimValue(1 if (lv != 0 and rv != 0) else 0, 1)
            if node.op == "||": return SimValue(1 if (lv != 0 or rv != 0) else 0, 1)
            if node.op in ("<<", "<<<"): return SimValue(lv << rv, w)
            if node.op in (">>", ">>>"): return SimValue(lv >> rv, w)

        if isinstance(node, TernaryOpNode):
            cond = self.eval_expr(node.condition, env)
            return self.eval_expr(node.true_expr, env) if cond.get_int() != 0 else self.eval_expr(node.false_expr, env)

        if isinstance(node, ConcatNode):
            tot_val = 0
            tot_w = 0
            for elem in reversed(node.elements):
                ev = self.eval_expr(elem, env)
                tot_val |= (ev.get_int() << tot_w)
                tot_w += ev.width
            return SimValue(tot_val, max(1, tot_w))

        return SimValue(0, 1)

    def exec_statement(self, stmt: Any, is_clock_edge: bool = False, local_env: Dict[str, SimValue] = None):
        if not stmt: return
        env = local_env or self.signals

        if isinstance(stmt, ProceduralAssignNode):
            rhs_val = self.eval_expr(stmt.rhs, env)
            if isinstance(stmt.lhs, IdentifierNode):
                var_name = stmt.lhs.name
                w = self.signal_widths.get(var_name, rhs_val.width)
                new_v = SimValue(rhs_val.get_int(), w)
                if stmt.is_non_blocking:
                    self.nba_queue.append((var_name, new_v))
                else:
                    env[var_name] = new_v
            elif isinstance(stmt.lhs, BitSelectNode):
                var_name = stmt.lhs.target.name if isinstance(stmt.lhs.target, IdentifierNode) else ""
                if var_name in env:
                    curr = env[var_name].get_int()
                    idx = self.eval_expr(stmt.lhs.msb, env).get_int()
                    bit_val = rhs_val.get_int() & 1
                    updated = (curr & ~(1 << idx)) | (bit_val << idx)
                    w = self.signal_widths.get(var_name, 1)
                    new_v = SimValue(updated, w)
                    if stmt.is_non_blocking:
                        self.nba_queue.append((var_name, new_v))
                    else:
                        env[var_name] = new_v

        elif hasattr(stmt, "statements"):
            for s in stmt.statements:
                self.exec_statement(s, is_clock_edge, env)

        elif isinstance(stmt, IfNode):
            cond_val = self.eval_expr(stmt.condition, env).get_int()
            if cond_val != 0:
                self.exec_statement(stmt.then_branch, is_clock_edge, env)
            elif stmt.else_branch:
                self.exec_statement(stmt.else_branch, is_clock_edge, env)

        elif isinstance(stmt, CaseNode):
            val = self.eval_expr(stmt.expr, env).get_int()
            matched = False
            for ci in stmt.items:
                if ci.is_default: continue
                for cond in ci.conditions:
                    c_val = self.eval_expr(cond, env).get_int()
                    if c_val == val:
                        self.exec_statement(ci.body, is_clock_edge, env)
                        matched = True
                        break
                if matched: break
            if not matched:
                for ci in stmt.items:
                    if ci.is_default:
                        self.exec_statement(ci.body, is_clock_edge, env)
                        break

    def evaluate_combinational(self, max_iterations: int = 15):
        for _ in range(max_iterations):
            changed = False
            for item in self.module.items:
                if isinstance(item, AssignNode):
                    rhs_val = self.eval_expr(item.rhs)
                    if isinstance(item.lhs, IdentifierNode):
                        sig_name = item.lhs.name
                        w = self.signal_widths.get(sig_name, rhs_val.width)
                        new_v = SimValue(rhs_val.get_int(), w)
                        if self.signals.get(sig_name) is None or self.signals[sig_name].get_int() != new_v.get_int():
                            self.signals[sig_name] = new_v
                            changed = True

            for item in self.module.items:
                if isinstance(item, AlwaysNode):
                    is_seq = any(s.edge in ("posedge", "negedge") for s in item.sensitivity)
                    if not is_seq:
                        old_snap = {k: v.get_int() for k, v in self.signals.items()}
                        self.exec_statement(item.body, is_clock_edge=False)
                        for s_name, s_val in self.nba_queue:
                            self.signals[s_name] = s_val
                        self.nba_queue.clear()
                        for k, old_v in old_snap.items():
                            if self.signals[k].get_int() != old_v:
                                changed = True
            if not changed:
                break

    def step_clock(self, clk_name: Optional[str] = None):
        cname = clk_name or (self.clock_signals[0] if self.clock_signals else "clk")
        self.evaluate_combinational()

        for item in self.module.items:
            if isinstance(item, AlwaysNode):
                is_posedge = any(s.edge == "posedge" and (s.signal == cname or s.signal in self.reset_signals) for s in item.sensitivity)
                if is_posedge:
                    self.exec_statement(item.body, is_clock_edge=True)

        for sig_name, val in self.nba_queue:
            self.signals[sig_name] = val
        self.nba_queue.clear()

        self.evaluate_combinational()
        self.time_step += 1

class UserTBSimulator:
    """Executes the user's testbench against the DUT and captures stdout from $display."""
    def __init__(self, dut_module: ModuleNode, tb_module: ModuleNode):
        self.dut_module = dut_module
        self.tb_module = tb_module
        self.dut = RTLSimulator(dut_module)
        self.tb_signals: Dict[str, SimValue] = {}
        self.tb_widths: Dict[str, int] = {}
        self.port_mapping: Dict[str, str] = {} # tb_signal -> dut_port
        self.stdout_lines: List[str] = []
        self.sim_time = 0
        self.clock_toggles = 0
        self.reset_values_seen: Set[int] = set()
        self.inputs_driven = False
        self.outputs_observed = False
        self.self_checking = False
        self.simulation_finished = False
        self.clock_half_period = 5
        self.clk_sig_name = "clk"
        self.checks_passed = 0
        self.checks_failed = 0

        self._setup_testbench()

    def _setup_testbench(self):
        # 1. Discover signals declared in testbench
        for p in getattr(self.tb_module, "ports", []):
            self.tb_signals[p.name] = SimValue(0, 1)
            self.tb_widths[p.name] = 1

        for it in getattr(self.tb_module, "items", []):
            if isinstance(it, SignalDeclNode):
                w = 1
                if it.width_msb and hasattr(it.width_msb, "value"):
                    w = it.width_msb.value + 1
                self.tb_signals[it.name] = SimValue(0, w)
                self.tb_widths[it.name] = w

        # 2. Discover DUT instance port connection
        found_instance = False
        for it in getattr(self.tb_module, "items", []):
            if isinstance(it, InstanceNode):
                found_instance = True
                for formal, actual in it.port_map.items():
                    act_name = getattr(actual, "name", None)
                    if act_name:
                        actual_formal = formal
                        if formal.startswith("port_"):
                            try:
                                idx = int(formal.split("_")[1])
                                if idx < len(self.dut_module.ports):
                                    actual_formal = self.dut_module.ports[idx].name
                            except Exception:
                                pass
                        self.port_mapping[act_name] = actual_formal
                        self.port_mapping[actual_formal] = act_name

        # Fallback port connection by identical name
        for dp in self.dut_module.ports:
            if dp.name in self.tb_signals and dp.name not in self.port_mapping:
                self.port_mapping[dp.name] = dp.name

        # 3. Detect clock toggling definition
        for it in getattr(self.tb_module, "items", []):
            if isinstance(it, AlwaysNode):
                body_str = str(it.body)
                if "clk" in body_str:
                    self.clk_sig_name = "clk"
                    # Scan for #delay
                    for sub in getattr(it.body, "statements", [it.body]):
                        if isinstance(sub, DelayNode):
                            try: self.clock_half_period = int(sub.delay_val)
                            except Exception: pass

    def sync_tb_to_dut(self):
        for tb_name, val in self.tb_signals.items():
            dut_port = self.port_mapping.get(tb_name, tb_name)
            if dut_port in self.dut.ports and self.dut.ports[dut_port] == "input":
                self.dut.set_input(dut_port, val.get_int())
                self.inputs_driven = True

        self.dut.evaluate_combinational()

    def sync_dut_to_tb(self):
        for dut_port, p_type in self.dut.ports.items():
            if p_type == "output":
                tb_name = self.port_mapping.get(dut_port, dut_port)
                val = self.dut.get_signal(dut_port)
                w = self.dut.signal_widths.get(dut_port, 1)
                self.tb_signals[tb_name] = SimValue(val, w)

    def eval_tb_expr(self, expr: Any) -> SimValue:
        self.sync_dut_to_tb()
        return self.dut.eval_expr(expr, local_env=self.tb_signals)

    def advance_time(self, delay: int):
        target_time = self.sim_time + delay
        step = self.clock_half_period or 5

        while self.sim_time < target_time:
            self.sim_time += step
            # Toggle clock if clock signal exists
            if self.clk_sig_name in self.tb_signals:
                cur_clk = self.tb_signals[self.clk_sig_name].get_int()
                new_clk = 1 if cur_clk == 0 else 0
                self.tb_signals[self.clk_sig_name] = SimValue(new_clk, 1)
                self.clock_toggles += 1
                self.sync_tb_to_dut()

                if new_clk == 1:
                    # posedge clock triggers DUT sequential logic!
                    self.dut.step_clock()
                    self.sync_dut_to_tb()
            else:
                self.dut.evaluate_combinational()
                self.sync_dut_to_tb()

    def format_display_string(self, args: List[Any]) -> str:
        if not args: return ""
        raw_fmt = getattr(args[0], "name", str(args[0])).strip('"')
        arg_vals = [self.eval_tb_expr(a).get_int() for a in args[1:]]

        val_idx = 0
        def repl(m):
            nonlocal val_idx
            spec = m.group(0)
            if val_idx >= len(arg_vals): return spec
            v = arg_vals[val_idx]
            val_idx += 1
            if spec in ("%d", "%0d"): return str(v)
            if spec in ("%h", "%0h", "%x", "%0x"): return hex(v)[2:].upper()
            if spec in ("%b", "%0b"): return bin(v)[2:]
            if spec == "%s": return str(v)
            return str(v)

        res = re.sub(r'%[0-9]*[dhbxcso]', repl, raw_fmt)
        # If there were extra arguments not consumed by format specifiers, append them
        if val_idx < len(arg_vals):
            extra = " ".join(str(arg_vals[i]) for i in range(val_idx, len(arg_vals)))
            res = (res + " " + extra).strip()
        return res

    def exec_tb_stmt(self, stmt: Any):
        if not stmt or self.simulation_finished:
            return

        if isinstance(stmt, DelayNode):
            try: delay = int(stmt.delay_val)
            except Exception: delay = 10
            self.advance_time(delay)

        elif isinstance(stmt, ProceduralAssignNode):
            val = self.eval_tb_expr(stmt.rhs)
            var_name = getattr(stmt.lhs, "name", "")
            if var_name:
                w = self.tb_widths.get(var_name, val.width)
                self.tb_signals[var_name] = SimValue(val.get_int(), w)
                self.sync_tb_to_dut()

                if "rst" in var_name.lower() or "reset" in var_name.lower():
                    self.reset_values_seen.add(val.get_int())

        elif isinstance(stmt, SystemTaskNode):
            if stmt.task_name in ("$display", "$write", "$monitor", "$strobe"):
                line = self.format_display_string(stmt.args)
                self.stdout_lines.append(line)
                self.outputs_observed = True
            elif stmt.task_name == "$finish":
                self.simulation_finished = True

        elif isinstance(stmt, AssertNode):
            self.self_checking = True
            self.outputs_observed = True
            cond_v = self.eval_tb_expr(stmt.condition).get_int()
            if cond_v != 0:
                self.checks_passed += 1
            else:
                self.checks_failed += 1
                if stmt.else_action:
                    self.exec_tb_stmt(stmt.else_action)
                else:
                    self.stdout_lines.append(f"ASSERTION FAILED at simulation time {self.sim_time}")

        elif isinstance(stmt, IfNode):
            cond_v = self.eval_tb_expr(stmt.condition).get_int()
            cond_str = str(getattr(stmt.condition, "name", str(stmt.condition)))
            dut_outputs = [p.name for p in getattr(self.dut_module, "ports", []) if p.direction == "output"]
            if any(out in cond_str for out in dut_outputs):
                self.outputs_observed = True
                body_str = str(stmt.then_branch) + (" " + str(stmt.else_branch) if stmt.else_branch else "")
                if any(err in body_str.lower() for err in ("error", "fail", "mismatch", "incorrect", "$fatal", "$error")):
                    self.self_checking = True
                    if cond_v != 0:
                        self.checks_failed += 1
                    else:
                        self.checks_passed += 1

            if cond_v != 0:
                self.exec_tb_stmt(stmt.then_branch)
            elif stmt.else_branch:
                self.exec_tb_stmt(stmt.else_branch)

        elif hasattr(stmt, "statements"):
            for s in stmt.statements:
                if self.simulation_finished: break
                self.exec_tb_stmt(s)

    def run(self) -> Dict[str, Any]:
        t0 = time.time()

        # Find initial block(s) in testbench
        initial_blocks = [it for it in getattr(self.tb_module, "items", []) if isinstance(it, InitialNode)]

        if not initial_blocks:
            return {
                "executed": False,
                "exit_code": 1,
                "reason": "Testbench contains no 'initial begin ... end' stimulus block.",
                "stdout": "",
                "stdout_lines": [],
                "checks_passed": 0,
                "checks_failed": 0,
                "self_checking": False,
                "tb_quality": {
                    "clock_present": self.clock_toggles > 0,
                    "reset_tested": 0 in self.reset_values_seen and 1 in self.reset_values_seen,
                    "dut_instantiated": len(self.port_mapping) > 0,
                    "inputs_driven": False,
                    "outputs_observed": False,
                    "outputs_checked": False,
                    "self_checking": False,
                    "simulation_ends": False,
                    "status": "INVALID"
                }
            }

        # Initialize DUT
        self.dut.evaluate_combinational()

        for ib in initial_blocks:
            self.exec_tb_stmt(ib.body)
            if self.simulation_finished:
                break

        duration_ms = round((time.time() - t0) * 1000, 2)

        # Quality metrics
        clk_ok = self.clock_toggles >= 2 or len(self.dut.clock_signals) == 0
        rst_ok = (0 in self.reset_values_seen and 1 in self.reset_values_seen) or len(self.dut.reset_signals) == 0
        dut_ok = len(self.port_mapping) > 0
        inps_ok = self.inputs_driven
        outs_ok = self.outputs_observed
        has_self_checks = self.self_checking and (self.checks_passed > 0 or self.checks_failed > 0)
        sim_ok = self.simulation_finished or self.sim_time > 0

        status = "VALID" if (clk_ok and rst_ok and inps_ok) else ("INCOMPLETE" if inps_ok else "INVALID")

        return {
            "executed": True,
            "exit_code": 0 if self.checks_failed == 0 else 1,
            "duration_ms": duration_ms,
            "simulation_time_units": self.sim_time,
            "stdout": "\n".join(self.stdout_lines),
            "stdout_lines": self.stdout_lines,
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_failed,
            "self_checking": self.self_checking,
            "tb_quality": {
                "clock_present": clk_ok,
                "reset_tested": rst_ok,
                "dut_instantiated": dut_ok,
                "inputs_driven": inps_ok,
                "outputs_observed": outs_ok,
                "outputs_checked": has_self_checks,
                "self_checking": self.self_checking,
                "simulation_ends": sim_ok,
                "status": status
            }
        }
