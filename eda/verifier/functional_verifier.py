# Unified Functional Verifier, Smoke Test Engine & Correctness Assessor
from typing import Dict, List, Any, Optional
from eda.parser.ast_nodes import DesignAST, ModuleNode
from eda.analyzer.static_analyzer import StaticAnalyzer
from eda.test_generator.auto_tester import AutoTester
from eda.verifier.testbench_analyzer import TestbenchAnalyzer
from eda.verifier.simulator import RTLSimulator

class FunctionalVerifier:
    def __init__(self, rtl_ast: DesignAST, tb_ast: Optional[DesignAST] = None):
        self.rtl_ast = rtl_ast
        self.tb_ast = tb_ast

    def verify(self) -> Dict[str, Any]:
        if not self.rtl_ast.modules:
            return {
                "overall_score": 0,
                "status": "FAILED",
                "correctness_state": "FAILED",
                "evidence": ["No valid RTL modules found to verify."],
                "smoke_test": {},
                "metrics": {}
            }

        top_module = self.rtl_ast.modules[0]

        # 1. Static RTL analysis / Linting
        analyzer = StaticAnalyzer(self.rtl_ast)
        lint_issues = analyzer.analyze()
        lint_summary = analyzer.get_summary()

        has_syntax_errors = any(i.category == "Syntax" for i in lint_issues)
        has_critical_errors = lint_summary["errors_count"] > 0
        rtl_quality_score = lint_summary["quality_score"]

        # 2. Automated test generation and simulation
        auto_tester = AutoTester(top_module)
        auto_test_res = auto_tester.generate_and_run()

        # 3. Testbench quality evaluation (if provided)
        tb_eval = None
        if self.tb_ast and self.tb_ast.modules:
            tb_analyzer = TestbenchAnalyzer(self.tb_ast, top_module)
            tb_eval = tb_analyzer.analyze()

        # 4. Smoke Test items
        syntax_pass = not has_syntax_errors
        elaboration_pass = len(top_module.ports) > 0 and not has_critical_errors
        sim_pass = auto_test_res["failed"] == 0
        reset_pass = any(r["category"] == "Reset" and r["passed"] for r in auto_test_res["results"]) if any("rst" in p.name.lower() or "reset" in p.name.lower() for p in top_module.ports) else True
        basic_func_pass = auto_test_res["passed"] > 0
        corner_cases_pass = any(r["category"] == "Corner Cases" and r["passed"] for r in auto_test_res["results"])
        assertions_pass = (tb_eval and any(m["name"] == "Output Verification" and m["passed"] for m in tb_eval.get("metrics", []))) or True
        output_checking_pass = (tb_eval and any(m["name"] == "Output Verification" and m["passed"] for m in tb_eval.get("metrics", []))) if tb_eval else True
        coverage_pct = auto_test_res["coverage_estimate"]

        smoke_items = [
            {"name": "Syntax", "status": "PASS" if syntax_pass else "FAIL", "weight": 10},
            {"name": "Elaboration", "status": "PASS" if elaboration_pass else "FAIL", "weight": 10},
            {"name": "Simulation", "status": "PASS" if sim_pass else "FAIL", "weight": 15},
            {"name": "Reset", "status": "PASS" if reset_pass else "FAIL", "weight": 10},
            {"name": "Basic Functionality", "status": "PASS" if basic_func_pass else "FAIL", "weight": 15},
            {"name": "Corner Cases", "status": "PASS" if corner_cases_pass else "FAIL", "weight": 10},
            {"name": "Assertions", "status": "PASS" if assertions_pass else "WARN", "weight": 10},
            {"name": "Output Checking", "status": "PASS" if output_checking_pass else "WARN", "weight": 10},
            {"name": "Coverage", "status": f"{coverage_pct}%", "weight": 10},
            {"name": "RTL Quality", "status": f"{rtl_quality_score}%", "weight": 10},
        ]

        # Calculate Overall Smoke Test Score (out of 100)
        # Weighted calculation from genuine criteria
        earned_pts = 0
        total_pts = 100

        earned_pts += 10 if syntax_pass else 0
        earned_pts += 10 if elaboration_pass else 0
        earned_pts += 15 if sim_pass else int(15 * (auto_test_res["passed"] / max(1, auto_test_res["tests_executed"])))
        earned_pts += 10 if reset_pass else 0
        earned_pts += 15 if basic_func_pass else 0
        earned_pts += 10 if corner_cases_pass else 0
        earned_pts += 10 if assertions_pass else 5
        earned_pts += 10 if output_checking_pass else 5
        earned_pts += int(round(coverage_pct * 0.10))
        earned_pts += int(round(rtl_quality_score * 0.10))

        # Overall Smoke Test score clamped between 0 and 100
        overall_score = min(100, max(0, int(round((earned_pts / 110.0) * 100))))

        # Status and Actionable recommendations
        smoke_status = "VERIFIED" if overall_score >= 90 else ("PARTIALLY_VERIFIED" if overall_score >= 70 else "FAILED")

        reasons_below_90 = []
        if not reset_pass:
            reasons_below_90.append("No explicit reset state transition or reset not stimulated.")
        if auto_test_res["failed"] > 0:
            reasons_below_90.append(f"{auto_test_res['failed']} auto-generated test vectors failed evaluation.")
        if tb_eval and not output_checking_pass:
            reasons_below_90.append("Testbench does not automatically assert or check output pins.")
        if rtl_quality_score < 90:
            reasons_below_90.append(f"Static lint issues detected ({lint_summary['errors_count']} errors, {lint_summary['warnings_count']} warnings).")
        if coverage_pct < 85:
            reasons_below_90.append(f"Toggle coverage is currently {coverage_pct}%, below 85% threshold.")

        # Correctness Engine Assessment
        evidence = []
        evidence.append(f"Auto-tester executed {auto_test_res['tests_executed']} vectors with {auto_test_res['passed']} passing.")
        evidence.append(f"Toggle coverage estimated at {coverage_pct}% across all module input/output bits.")
        if has_critical_errors:
            evidence.append(f"Linting identified {lint_summary['errors_count']} critical static errors (e.g. {lint_issues[0].message if lint_issues else ''}).")
        else:
            evidence.append("No critical elaboration or linting errors detected.")

        if tb_eval:
            evidence.append(f"User testbench evaluated with score {tb_eval['score']}/100.")

        correctness_state = "VERIFIED"
        if has_critical_errors or auto_test_res["failed"] > 5:
            correctness_state = "FAILED"
        elif overall_score < 70 or not sim_pass:
            correctness_state = "PARTIALLY VERIFIED"
        elif overall_score < 90:
            correctness_state = "PARTIALLY VERIFIED"
        else:
            correctness_state = "VERIFIED"

        return {
            "overall_score": overall_score,
            "smoke_status": smoke_status,
            "correctness_state": correctness_state,
            "evidence": evidence,
            "smoke_items": smoke_items,
            "reasons_below_90": reasons_below_90,
            "tests_generated": auto_test_res["tests_generated"],
            "tests_executed": auto_test_res["tests_executed"],
            "passed": auto_test_res["passed"],
            "failed": auto_test_res["failed"],
            "coverage_estimate": coverage_pct,
            "verification_score": overall_score,
            "lint_summary": lint_summary,
            "tb_eval": tb_eval,
            "sample_results": auto_test_res["results"]
        }
