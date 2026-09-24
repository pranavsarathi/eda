# Static RTL Analysis & Quality Linting Engine
from typing import Dict, List, Any, Set, Tuple, Optional

try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False

    class _SimpleDiGraph:
        def __init__(self):
            self.adj = {}
        def add_edge(self, u, v):
            if u not in self.adj:
                self.adj[u] = []
            if v not in self.adj[u]:
                self.adj[u].append(v)
            if v not in self.adj:
                self.adj[v] = []

    def _simple_cycles(graph):
        adj = getattr(graph, 'adj', {})
        visited = set()
        stack = []
        stack_set = set()
        cycles = []
        def dfs(node):
            visited.add(node)
            stack.append(node)
            stack_set.add(node)
            for neighbor in adj.get(node, []):
                if neighbor in stack_set:
                    idx = stack.index(neighbor)
                    cycles.append(stack[idx:])
                elif neighbor not in visited:
                    dfs(neighbor)
            stack_set.remove(node)
            stack.pop()
        for n in list(adj.keys()):
            if n not in visited:
                dfs(n)
        return cycles

    class _NxShim:
        DiGraph = _SimpleDiGraph
        simple_cycles = staticmethod(_simple_cycles)
    nx = _NxShim()

from eda.parser.ast_nodes import (
    DesignAST, ModuleNode, PortNode, SignalDeclNode, AssignNode,
    AlwaysNode, IfNode, CaseNode, ProceduralAssignNode, BinaryOpNode,
    UnaryOpNode, TernaryOpNode, IdentifierNode, NumberNode, BitSelectNode,
    ConcatNode, ReplicateNode, InstanceNode
)

class IssueCategory:
    SYNTAX = "Syntax"
    UNDECLARED_SIGNAL = "Undeclared Signal"
    MULTIPLE_DRIVERS = "Multiple Drivers"
    WIDTH_MISMATCH = "Width Mismatch"
    LATCH_INFERENCE = "Latch Inference"
    COMBINATIONAL_LOOP = "Combinational Loop"
    SENSITIVITY_LIST = "Sensitivity List"
    UNUSED_SIGNAL = "Unused Signal"
    UNDRIVEN_OUTPUT = "Undriven Output"
    MISSING_RESET = "Missing Reset"
    UNREACHABLE_FSM = "Unreachable FSM State"

class IssueSeverity:
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"

class LintIssue:
    def __init__(self, category: str, severity: str, message: str, line: int = 1, col: int = 1, signal: str = "", module: str = "", fix_suggestion: str = ""):
        self.category = category
        self.severity = severity
        self.message = message
        self.line = line
        self.col = col
        self.signal = signal
        self.module = module
        self.fix_suggestion = fix_suggestion

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "severity": self.severity,
            "message": self.message,
            "line": self.line,
            "col": self.col,
            "signal": self.signal,
            "module": self.module,
            "fix_suggestion": self.fix_suggestion
        }

class StaticAnalyzer:
    def __init__(self, ast: DesignAST):
        self.ast = ast
        self.issues: List[LintIssue] = []

    def get_signal_names_in_expr(self, node: Any) -> Set[str]:
        """Extract all identifier signal names referenced in an expression."""
        signals = set()
        if not node:
            return signals

        if isinstance(node, IdentifierNode):
            signals.add(node.name)
        elif isinstance(node, BitSelectNode):
            signals |= self.get_signal_names_in_expr(node.target)
            signals |= self.get_signal_names_in_expr(node.msb)
            if node.lsb:
                signals |= self.get_signal_names_in_expr(node.lsb)
        elif isinstance(node, BinaryOpNode):
            signals |= self.get_signal_names_in_expr(node.left)
            signals |= self.get_signal_names_in_expr(node.right)
        elif isinstance(node, UnaryOpNode):
            signals |= self.get_signal_names_in_expr(node.expr)
        elif isinstance(node, TernaryOpNode):
            signals |= self.get_signal_names_in_expr(node.condition)
            signals |= self.get_signal_names_in_expr(node.true_expr)
            signals |= self.get_signal_names_in_expr(node.false_expr)
        elif isinstance(node, ConcatNode):
            for elem in node.elements:
                signals |= self.get_signal_names_in_expr(elem)
        elif isinstance(node, ReplicateNode):
            signals |= self.get_signal_names_in_expr(node.expr)
        return signals

    def get_assigned_signals_in_stmt(self, stmt: Any) -> List[Tuple[str, int, int]]:
        """Extract all (signal_name, line, col) assigned within a statement."""
        res = []
        if not stmt:
            return res

        if isinstance(stmt, ProceduralAssignNode):
            names = self.get_signal_names_in_expr(stmt.lhs)
            for n in names:
                res.append((n, stmt.line, stmt.col))
        elif hasattr(stmt, "statements"):
            for s in stmt.statements:
                res.extend(self.get_assigned_signals_in_stmt(s))
        elif isinstance(stmt, IfNode):
            res.extend(self.get_assigned_signals_in_stmt(stmt.then_branch))
            if stmt.else_branch:
                res.extend(self.get_assigned_signals_in_stmt(stmt.else_branch))
        elif isinstance(stmt, CaseNode):
            for item in stmt.items:
                res.extend(self.get_assigned_signals_in_stmt(item.body))
        return res

    def evaluate_constant(self, node: Any, param_env: Dict[str, int]) -> Optional[int]:
        if not node:
            return None
        if isinstance(node, NumberNode):
            return node.value
        if isinstance(node, IdentifierNode):
            return param_env.get(node.name)
        if isinstance(node, BinaryOpNode):
            l = self.evaluate_constant(node.left, param_env)
            r = self.evaluate_constant(node.right, param_env)
            if l is not None and r is not None:
                if node.op == "+": return l + r
                if node.op == "-": return l - r
                if node.op == "*": return l * r
                if node.op == "/": return l // r if r != 0 else 0
                if node.op == "<<": return l << r
                if node.op == ">>": return l >> r
        return None

    def get_signal_width(self, name: str, declared_widths: Dict[str, int]) -> int:
        return declared_widths.get(name, 1)

    def analyze_module(self, mod: ModuleNode):
        mod_name = mod.name

        # 1. Collect declared signals & parameters
        param_env = {}
        for p in mod.parameters:
            val = self.evaluate_constant(p.value, param_env)
            if val is not None:
                param_env[p.name] = val
            else:
                param_env[p.name] = 1

        declared_signals: Dict[str, Dict[str, Any]] = {}
        declared_widths: Dict[str, int] = {}
        port_directions: Dict[str, str] = {}

        for port in mod.ports:
            port_directions[port.name] = port.direction
            msb_val = self.evaluate_constant(port.width_msb, param_env) if port.width_msb else None
            lsb_val = self.evaluate_constant(port.width_lsb, param_env) if port.width_lsb else 0
            width = 1
            if msb_val is not None:
                width = abs(msb_val - (lsb_val or 0)) + 1
            declared_signals[port.name] = {"type": "port", "dir": port.direction, "width": width, "line": port.line}
            declared_widths[port.name] = width

        for item in mod.items:
            if isinstance(item, SignalDeclNode):
                msb_val = self.evaluate_constant(item.width_msb, param_env) if item.width_msb else None
                lsb_val = self.evaluate_constant(item.width_lsb, param_env) if item.width_lsb else 0
                width = 1
                if msb_val is not None:
                    width = abs(msb_val - (lsb_val or 0)) + 1
                declared_signals[item.name] = {"type": item.decl_type, "width": width, "line": item.line}
                declared_widths[item.name] = width

        # 2. Driver and Reader tracking
        drivers: Dict[str, List[Dict[str, Any]]] = {} # signal -> list of {line, type, expr}
        readers: Dict[str, List[int]] = {}           # signal -> list of line numbers

        # Dependency graph for combinational loops
        comb_dep_graph = nx.DiGraph()

        for item in mod.items:
            # Continuous assigns
            if isinstance(item, AssignNode):
                lhs_signals = self.get_signal_names_in_expr(item.lhs)
                rhs_signals = self.get_signal_names_in_expr(item.rhs)

                for ls in lhs_signals:
                    drivers.setdefault(ls, []).append({"line": item.line, "type": "continuous_assign"})
                    for rs in rhs_signals:
                        comb_dep_graph.add_edge(rs, ls) # rs drives ls

                for rs in rhs_signals:
                    readers.setdefault(rs, []).append(item.line)

                # Width mismatch check on assign
                for ls in lhs_signals:
                    l_width = declared_widths.get(ls, 1)
                    if isinstance(item.rhs, NumberNode) and item.rhs.width:
                        if item.rhs.width != l_width:
                            self.issues.append(LintIssue(
                                IssueCategory.WIDTH_MISMATCH,
                                IssueSeverity.WARNING,
                                f"Width mismatch in continuous assign to '{ls}': LHS width is {l_width} bits, but RHS is {item.rhs.width} bits.",
                                item.line, item.col, ls, mod_name,
                                f"Adjust RHS bit width to {l_width}'h..."
                            ))

            # Always blocks
            elif isinstance(item, AlwaysNode):
                is_sequential = False
                clock_signal = None
                reset_signal = None
                reset_type = None
                reset_polarity = "ACTIVE_HIGH"

                for sens in item.sensitivity:
                    if sens.edge in ("posedge", "negedge"):
                        is_sequential = True
                        sig_lower = sens.signal.lower()
                        if "clk" in sig_lower or "clock" in sig_lower:
                            clock_signal = sens.signal
                        elif "rst" in sig_lower or "reset" in sig_lower:
                            reset_signal = sens.signal
                            reset_type = "ASYNCHRONOUS"
                            reset_polarity = "ACTIVE_LOW" if sens.edge == "negedge" else "ACTIVE_HIGH"
                        else:
                            clock_signal = sens.signal

                # Collect all signals read in always block body and sensitivity for unused signal tracking
                def collect_all_reads(node):
                    r = set()
                    if not node: return r
                    if isinstance(node, ProceduralAssignNode):
                        r |= self.get_signal_names_in_expr(node.rhs)
                    elif isinstance(node, IfNode):
                        r |= self.get_signal_names_in_expr(node.condition)
                        r |= collect_all_reads(node.then_branch)
                        if node.else_branch: r |= collect_all_reads(node.else_branch)
                    elif isinstance(node, CaseNode):
                        r |= self.get_signal_names_in_expr(node.expr)
                        for ci in node.items:
                            for c in ci.conditions:
                                r |= self.get_signal_names_in_expr(c)
                            r |= collect_all_reads(ci.body)
                    elif hasattr(node, "statements"):
                        for s in node.statements:
                            r |= collect_all_reads(s)
                    return r

                always_reads = collect_all_reads(item.body)
                for s in item.sensitivity:
                    if s.signal and s.signal != "*":
                        always_reads.add(s.signal)
                for rs in always_reads:
                    readers.setdefault(rs, []).append(item.line)

                # Check for synchronous reset if asynchronous reset was not in sensitivity
                if is_sequential and not reset_signal:
                    top_stmt = item.body
                    if hasattr(top_stmt, "statements") and len(top_stmt.statements) > 0:
                        top_stmt = top_stmt.statements[0]
                    if isinstance(top_stmt, IfNode):
                        cond = top_stmt.condition
                        cond_sigs = self.get_signal_names_in_expr(cond)
                        for cs in cond_sigs:
                            cs_lower = cs.lower()
                            if "rst" in cs_lower or "reset" in cs_lower or (cs in port_directions and ("rst" in cs_lower or "reset" in cs_lower)):
                                reset_signal = cs
                                reset_type = "SYNCHRONOUS"
                                if isinstance(cond, UnaryOpNode) and cond.op in ("!", "~"):
                                    reset_polarity = "ACTIVE_LOW"
                                elif isinstance(cond, BinaryOpNode) and cond.op in ("==", "==="):
                                    if isinstance(cond.right, NumberNode) and cond.right.value == 0:
                                        reset_polarity = "ACTIVE_LOW"
                                    else:
                                        reset_polarity = "ACTIVE_HIGH"
                                else:
                                    reset_polarity = "ACTIVE_HIGH"
                                break

                assigned_here = self.get_assigned_signals_in_stmt(item.body)
                # Deduplicate by signal name so an always block counts as ONE driver
                unique_sigs_in_block = {sig: (l, c) for sig, l, c in assigned_here}
                for sig, (l, c) in unique_sigs_in_block.items():
                    drivers.setdefault(sig, []).append({
                        "line": l,
                        "type": "sequential_always" if is_sequential else "combinational_always"
                    })

                # Sequential always block: check for reset
                if is_sequential:
                    if not reset_signal:
                        self.issues.append(LintIssue(
                            IssueCategory.MISSING_RESET,
                            IssueSeverity.WARNING,
                            f"Sequential block at line {item.line} sensitive to posedge/negedge lacks an explicit asynchronous/synchronous reset condition.",
                            item.line, item.col, "", mod_name,
                            "Add an explicit reset branch (e.g. if (!rst_n) or if (rst)) to ensure deterministic initial state upon power-up."
                        ))

                # Combinational always block: check for latch inference & sensitivity
                if not is_sequential:
                    # Check sensitivity list completeness
                    if item.always_type == "always":
                        sens_sigs = {s.signal for s in item.sensitivity if s.signal != "*"}
                        read_sigs = set()
                        # Extract read signals in body
                        def collect_reads(stmt):
                            r = set()
                            if not stmt: return r
                            if isinstance(stmt, ProceduralAssignNode):
                                r |= self.get_signal_names_in_expr(stmt.rhs)
                            elif isinstance(stmt, IfNode):
                                r |= self.get_signal_names_in_expr(stmt.condition)
                                r |= collect_reads(stmt.then_branch)
                                if stmt.else_branch:
                                    r |= collect_reads(stmt.else_branch)
                            elif isinstance(stmt, CaseNode):
                                r |= self.get_signal_names_in_expr(stmt.expr)
                                for ci in stmt.items:
                                    r |= collect_reads(ci.body)
                            elif hasattr(stmt, "statements"):
                                for s in stmt.statements:
                                    r |= collect_reads(s)
                            return r

                        read_in_body = collect_reads(item.body)
                        if "*" not in [s.signal for s in item.sensitivity]:
                            missing_sens = read_in_body - sens_sigs - {s for s, _, _ in assigned_here}
                            if missing_sens:
                                self.issues.append(LintIssue(
                                    IssueCategory.SENSITIVITY_LIST,
                                    IssueSeverity.WARNING,
                                    f"Incomplete sensitivity list in combinational always block at line {item.line}. Missing signals: {', '.join(sorted(missing_sens))}.",
                                    item.line, item.col, list(missing_sens)[0], mod_name,
                                    "Use always @(*) or SystemVerilog always_comb to prevent simulation/synthesis mismatches."
                                ))

                    # Collect unconditional default assignments made at the outer level before conditionals
                    unconditional_defaults = set()
                    def collect_unconditional(node):
                        if isinstance(node, ProceduralAssignNode):
                            for n in self.get_signal_names_in_expr(node.lhs):
                                unconditional_defaults.add(n)
                        elif hasattr(node, "statements"):
                            for s in node.statements:
                                if isinstance(s, (IfNode, CaseNode)):
                                    break
                                collect_unconditional(s)
                    collect_unconditional(item.body)

                    # Check for latch inference in If statements
                    def check_latch(stmt, assigned_vars: Set[str]):
                        if isinstance(stmt, IfNode):
                            then_assigned = {s for s, _, _ in self.get_assigned_signals_in_stmt(stmt.then_branch)}
                            if not stmt.else_branch:
                                # Variable assigned in then, but no else => inferred latch!
                                for v in then_assigned:
                                    if v not in unconditional_defaults:
                                        self.issues.append(LintIssue(
                                            IssueCategory.LATCH_INFERENCE,
                                            IssueSeverity.ERROR,
                                            f"Inferred latch on signal '{v}' at line {stmt.line}: assigned in 'if' branch but missing 'else' branch in combinational block.",
                                            stmt.line, stmt.col, v, mod_name,
                                            f"Provide a default assignment for '{v}' at the top of the always block or add an 'else' branch."
                                        ))
                            else:
                                else_assigned = {s for s, _, _ in self.get_assigned_signals_in_stmt(stmt.else_branch)}
                                diff = then_assigned.symmetric_difference(else_assigned)
                                for v in diff:
                                    if v not in unconditional_defaults:
                                        self.issues.append(LintIssue(
                                            IssueCategory.LATCH_INFERENCE,
                                            IssueSeverity.ERROR,
                                            f"Inferred latch on signal '{v}' at line {stmt.line}: not assigned in all branches of if-else.",
                                            stmt.line, stmt.col, v, mod_name,
                                            f"Ensure '{v}' is assigned in both then and else branches."
                                        ))
                                check_latch(stmt.then_branch, assigned_vars)
                                check_latch(stmt.else_branch, assigned_vars)
                        elif isinstance(stmt, CaseNode):
                            # Check if default is present
                            has_default = any(ci.is_default for ci in stmt.items)
                            if not has_default:
                                self.issues.append(LintIssue(
                                    IssueCategory.LATCH_INFERENCE,
                                    IssueSeverity.WARNING,
                                    f"Case statement at line {stmt.line} is missing a 'default:' clause, risking unintentional latch inference.",
                                    stmt.line, stmt.col, "", mod_name,
                                    "Add a 'default:' branch to specify complete case coverage."
                                ))
                        elif hasattr(stmt, "statements"):
                            for s in stmt.statements:
                                check_latch(s, assigned_vars)

                    check_latch(item.body, {s for s, _, _ in assigned_here})

                    # Add to comb dependency graph
                    for sig, _, _ in assigned_here:
                        # Find all read signals
                        def find_reads(node):
                            r = set()
                            if isinstance(node, ProceduralAssignNode):
                                r |= self.get_signal_names_in_expr(node.rhs)
                            elif isinstance(node, IfNode):
                                r |= self.get_signal_names_in_expr(node.condition)
                                r |= find_reads(node.then_branch)
                                if node.else_branch: r |= find_reads(node.else_branch)
                            elif hasattr(node, "statements"):
                                for s in node.statements:
                                    r |= find_reads(s)
                            return r
                        reads = find_reads(item.body)
                        for rs in reads:
                            comb_dep_graph.add_edge(rs, sig)

        # 3. Check for multiple drivers
        for sig, drv_list in drivers.items():
            if len(drv_list) > 1:
                # Multiple drivers
                lines_str = ", ".join(f"L{d['line']} ({d['type']})" for d in drv_list)
                self.issues.append(LintIssue(
                    IssueCategory.MULTIPLE_DRIVERS,
                    IssueSeverity.ERROR,
                    f"Multiple drivers detected on signal '{sig}': assigned at {lines_str}.",
                    drv_list[1]["line"], 1, sig, mod_name,
                    f"Consolidate assignments to '{sig}' into a single always block or continuous assignment."
                ))

        # 4. Check for undeclared signals
        all_referenced_signals = set(drivers.keys()) | set(readers.keys())
        for sig in all_referenced_signals:
            if sig not in declared_signals and sig not in param_env:
                self.issues.append(LintIssue(
                    IssueCategory.UNDECLARED_SIGNAL,
                    IssueSeverity.ERROR,
                    f"Signal '{sig}' is referenced but never declared as input, output, wire, or reg.",
                    1, 1, sig, mod_name,
                    f"Declare signal '{sig}' as wire or reg with appropriate bit width."
                ))

        # 5. Check for combinational loops using NetworkX
        try:
            cycles = list(nx.simple_cycles(comb_dep_graph))
            for cycle in cycles:
                cycle_str = " -> ".join(cycle) + f" -> {cycle[0]}"
                self.issues.append(LintIssue(
                    IssueCategory.COMBINATIONAL_LOOP,
                    IssueSeverity.ERROR,
                    f"Combinational loop detected involving signals: {cycle_str}. This creates an unclocked feedback race condition.",
                    1, 1, cycle[0], mod_name,
                    "Break the combinational loop by introducing a clock-synchronous flip-flop register."
                ))
        except Exception:
            pass

        # 6. Check for undriven outputs
        for port_name, direction in port_directions.items():
            if direction == "output":
                if port_name not in drivers:
                    self.issues.append(LintIssue(
                        IssueCategory.UNDRIVEN_OUTPUT,
                        IssueSeverity.WARNING,
                        f"Output port '{port_name}' is declared but never assigned/driven in the module.",
                        declared_signals[port_name]["line"], 1, port_name, mod_name,
                        f"Assign an internal signal or logic value to output '{port_name}'."
                    ))

        # 7. Check for unused declared internal signals
        for sig_name, info in declared_signals.items():
            if info["type"] in ("wire", "reg", "logic") and port_directions.get(sig_name) != "input":
                if sig_name not in readers and port_directions.get(sig_name) != "output":
                    self.issues.append(LintIssue(
                        IssueCategory.UNUSED_SIGNAL,
                        IssueSeverity.WARNING,
                        f"Internal signal '{sig_name}' is declared at line {info['line']} but its value is never read or used downstream.",
                        info["line"], 1, sig_name, mod_name,
                        f"Remove unused signal '{sig_name}' or connect it to an output / datapath."
                    ))

    def analyze(self) -> List[LintIssue]:
        self.issues.clear()

        # Add parser syntax errors
        for err in self.ast.syntax_errors:
            self.issues.append(LintIssue(
                IssueCategory.SYNTAX,
                IssueSeverity.ERROR,
                err["message"],
                err.get("line", 1),
                err.get("col", 1),
                err.get("token", ""),
                fix_suggestion="Correct Verilog syntax error at specified line."
            ))

        for mod in self.ast.modules:
            self.analyze_module(mod)

        return self.issues

    def get_summary(self) -> Dict[str, Any]:
        errors = [i for i in self.issues if i.severity == IssueSeverity.ERROR]
        warnings = [i for i in self.issues if i.severity == IssueSeverity.WARNING]
        score = max(0, 100 - (len(errors) * 15 + len(warnings) * 4))
        return {
            "total_issues": len(self.issues),
            "errors_count": len(errors),
            "warnings_count": len(warnings),
            "quality_score": score,
            "status": "PASS" if len(errors) == 0 else "FAIL",
            "issues": [i.to_dict() for i in self.issues]
        }
