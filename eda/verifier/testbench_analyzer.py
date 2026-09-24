# Testbench Quality & Verification Coverage Analyzer
from typing import Dict, List, Any, Optional
from eda.parser.ast_nodes import (
    DesignAST, ModuleNode, PortNode, InitialNode, AlwaysNode,
    IfNode, SystemTaskNode, AssertNode, ProceduralAssignNode, DelayNode
)

class TBQualityMetric:
    def __init__(self, name: str, passed: bool, weight: int, score: int, details: str):
        self.name = name
        self.passed = passed
        self.weight = weight
        self.score = score
        self.details = details

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "weight": self.weight,
            "score": self.score,
            "details": self.details
        }

class TestbenchAnalyzer:
    def __init__(self, tb_ast: DesignAST, dut_module: Optional[ModuleNode] = None):
        self.tb_ast = tb_ast
        self.dut_module = dut_module
        self.metrics: List[TBQualityMetric] = []
        self.deficiencies: List[str] = []
        self.recommendations: List[str] = []

    def analyze(self) -> Dict[str, Any]:
        self.metrics.clear()
        self.deficiencies.clear()
        self.recommendations.clear()

        if not self.tb_ast.modules:
            return {
                "score": 0,
                "status": "NO_TESTBENCH",
                "deficiencies": ["No testbench module detected in provided code."],
                "recommendations": ["Write or generate a testbench with clock, reset, and stimulus."],
                "metrics": []
            }

        tb_mod = self.tb_ast.modules[0]

        # 1. Clock Generation Check
        has_clock_gen = False
        clock_period_detected = None
        for item in tb_mod.items:
            if isinstance(item, AlwaysNode):
                # e.g. always #5 clk = ~clk;
                has_clock_gen = True
            elif isinstance(item, InitialNode):
                def check_clk(stmt):
                    if isinstance(stmt, DelayNode) or isinstance(stmt, ProceduralAssignNode):
                        return True
                    if hasattr(stmt, "statements"):
                        return any(check_clk(s) for s in stmt.statements)
                    return False
                if check_clk(item.body):
                    pass

        # Check always blocks for clock toggling
        for item in tb_mod.items:
            if isinstance(item, AlwaysNode):
                body_str = str(item.body)
                if "~" in body_str or "!" in body_str or "clk" in body_str:
                    has_clock_gen = True

        if has_clock_gen:
            self.metrics.append(TBQualityMetric(
                "Clock Generation", True, 15, 15,
                "Free-running clock generation block detected."
            ))
        else:
            self.metrics.append(TBQualityMetric(
                "Clock Generation", False, 15, 0,
                "No clock toggling loop (always #5 clk = ~clk;) detected."
            ))
            self.deficiencies.append("Clock signal is not toggled continuously in testbench.")
            self.recommendations.append("Add: always #5 clk = ~clk; to drive sequential logic.")

        # 2. Reset Sequence Verification
        has_reset_assertion = False
        has_reset_deassertion = False
        for item in tb_mod.items:
            if isinstance(item, InitialNode):
                # Search procedural assigns for rst / rst_n
                def find_rst_assigns(stmt):
                    assigns = []
                    if isinstance(stmt, ProceduralAssignNode):
                        lhs_name = getattr(stmt.lhs, "name", "")
                        if "rst" in lhs_name.lower() or "reset" in lhs_name.lower():
                            val = getattr(stmt.rhs, "value", None)
                            assigns.append((lhs_name, val))
                    elif hasattr(stmt, "statements"):
                        for s in stmt.statements:
                            assigns.extend(find_rst_assigns(s))
                    return assigns

                rst_assigns = find_rst_assigns(item.body)
                if len(rst_assigns) >= 2:
                    has_reset_assertion = True
                    has_reset_deassertion = True
                elif len(rst_assigns) == 1:
                    has_reset_assertion = True

        if has_reset_assertion and has_reset_deassertion:
            self.metrics.append(TBQualityMetric(
                "Reset Testing", True, 20, 20,
                "Both reset assertion and release transitions were verified."
            ))
        elif has_reset_assertion:
            self.metrics.append(TBQualityMetric(
                "Reset Testing", False, 20, 10,
                "Reset asserted but deassertion transition or initial hold not fully exercised."
            ))
            self.deficiencies.append("Reset sequence is incomplete (asserted but not cleanly toggled).")
            self.recommendations.append("Assert reset for at least 2 clock cycles before deasserting.")
        else:
            self.metrics.append(TBQualityMetric(
                "Reset Testing", False, 20, 0,
                "No reset initialization or testing found in testbench."
            ))
            self.deficiencies.append("Missing reset verification test in testbench.")
            self.recommendations.append("Add reset pulse sequence (rst_n=0; #20 rst_n=1;).")

        # 3. Stimulus Quantity & Variation
        stimulus_count = 0
        boundary_tested = False
        for item in tb_mod.items:
            if isinstance(item, InitialNode):
                def count_stimuli(stmt):
                    cnt = 0
                    if isinstance(stmt, ProceduralAssignNode):
                        cnt += 1
                    elif isinstance(stmt, DelayNode):
                        cnt += 1
                    elif hasattr(stmt, "statements"):
                        for s in stmt.statements:
                            cnt += count_stimuli(s)
                    return cnt
                stimulus_count += count_stimuli(item.body)

        if stimulus_count >= 15:
            self.metrics.append(TBQualityMetric(
                "Stimulus Diversity", True, 20, 20,
                f"Sufficient stimulus variations applied ({stimulus_count} vector steps)."
            ))
        elif stimulus_count >= 5:
            self.metrics.append(TBQualityMetric(
                "Stimulus Diversity", True, 20, 14,
                f"Moderate stimulus applied ({stimulus_count} steps), but boundary cases may be missing."
            ))
            self.deficiencies.append("Limited input stimulus combinations exercised.")
            self.recommendations.append("Add additional corner cases (all 0s, all 1s, max value).")
        else:
            self.metrics.append(TBQualityMetric(
                "Stimulus Diversity", False, 20, 5,
                f"Insufficient stimulus: only {stimulus_count} stimulus statements found."
            ))
            self.deficiencies.append("Insufficient stimulus applied; design barely exercised.")
            self.recommendations.append("Apply a structured sequence of test vectors.")

        # 4. Output Checking & Assertions
        output_checks_count = 0
        has_assertions = False
        for item in tb_mod.items:
            def scan_checks(node):
                c = 0
                nonlocal has_assertions
                if isinstance(node, AssertNode):
                    has_assertions = True
                    c += 1
                elif isinstance(node, IfNode):
                    # e.g. if (out !== expected) $display("Error");
                    c += 1
                elif isinstance(node, SystemTaskNode):
                    if node.task_name in ("$display", "$monitor", "$strobe", "$fatal", "$error"):
                        c += 1
                if hasattr(node, "statements"):
                    for s in node.statements:
                        c += scan_checks(s)
                return c

            output_checks_count += scan_checks(item)

        if output_checks_count >= 5 or has_assertions:
            self.metrics.append(TBQualityMetric(
                "Output Verification", True, 25, 25,
                f"Self-checking verification logic found ({output_checks_count} assertion/display checks)."
            ))
        elif output_checks_count > 0:
            self.metrics.append(TBQualityMetric(
                "Output Verification", True, 25, 15,
                f"Partial output checking detected ({output_checks_count} checks), but some outputs not checked."
            ))
            self.deficiencies.append("Testbench does not rigorously check all outputs against golden references.")
            self.recommendations.append("Add explicit assertions or if (out != exp) error checks.")
        else:
            self.metrics.append(TBQualityMetric(
                "Output Verification", False, 25, 0,
                "No output checks or assertions found (testbench only drives inputs without verifying outputs!)."
            ))
            self.deficiencies.append("Outputs are never checked or compared against expected values.")
            self.recommendations.append("Convert testbench to a self-checking testbench.")

        # 5. Clean Termination ($finish)
        has_finish = False
        for item in tb_mod.items:
            def find_finish(node):
                if isinstance(node, SystemTaskNode) and node.task_name == "$finish":
                    return True
                if hasattr(node, "statements"):
                    return any(find_finish(s) for s in node.statements)
                return False
            if find_finish(item):
                has_finish = True
                break

        if has_finish:
            self.metrics.append(TBQualityMetric(
                "Simulation Termination", True, 10, 10,
                "$finish statement properly terminates simulation."
            ))
        else:
            self.metrics.append(TBQualityMetric(
                "Simulation Termination", False, 10, 3,
                "Missing $finish task; simulation may run indefinitely."
            ))
            self.recommendations.append("Add $finish at the end of the initial block.")

        # 6. Overall TB Score Calculation
        total_weight = sum(m.weight for m in self.metrics)
        earned_score = sum(m.score for m in self.metrics)
        final_score = int(round((earned_score / total_weight) * 100)) if total_weight > 0 else 0

        return {
            "score": final_score,
            "status": "PASS" if final_score >= 80 else ("MARGINAL" if final_score >= 50 else "DEFICIENT"),
            "metrics": [m.to_dict() for m in self.metrics],
            "deficiencies": self.deficiencies,
            "recommendations": self.recommendations
        }
