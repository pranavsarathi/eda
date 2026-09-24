# Canonical Single-Source Analysis Pipeline
import time
from typing import Dict, List, Any, Optional

from eda.parser.verilog_parser import parse_verilog
from eda.analyzer.static_analyzer import StaticAnalyzer
from eda.verifier.simulator import UserTBSimulator
from eda.hardware_inference.inferencer import HardwareInferencer
from eda.technology_model.tech_library import TechnologyModel
from eda.synthesis_estimator.estimator import SynthesisEstimator
from eda.floorplan_engine.floorplanner import FloorplanEngine
from eda.placement_engine.placer import PlacementEngine
from eda.cts_engine.cts_synthesizer import CTSSynthesizer
from eda.routing_engine.router import EstimatedRouter
from eda.timing_engine.sta_engine import STAEngine
from eda.power_engine.power_analyzer import PowerAnalyzer
from eda.efficiency_engine.efficiency_analyzer import EfficiencyAnalyzer
from eda.explanation_engine.why_engine import WhyEngine
from eda.replication_engine.script_generator import ReplicationScriptGenerator
from eda.report_generator.report_builder import ReportBuilder

def analyze_project(project: Dict[str, Any]) -> Dict[str, Any]:
    """
    Central, canonical analysis pipeline.
    User RTL + Testbench is the SINGLE SOURCE OF TRUTH.
    """
    start_time = time.time()
    rtl_code = project.get("rtl", "").strip()
    tb_code = project.get("tb", "").strip()
    tech_node = project.get("tech_node", "130nm")
    clock_mhz = float(project.get("clock_mhz", 100.0))
    core_util = float(project.get("core_util", 0.70))
    aspect_ratio = float(project.get("aspect_ratio", 1.0))
    routing_layers = int(project.get("routing_layers", 6))

    result = {
        "status": "READY",
        "top_module": "top",
        "elapsed_ms": 0,
        "compile": {
            "status": "PASS",
            "errors": [],
            "warnings": [],
            "modules": []
        },
        "simulation": {
            "executed": False,
            "exit_code": 0,
            "stdout": "",
            "stdout_lines": [],
            "reason": ""
        },
        "verification": {
            "status": "UNVERIFIED",
            "tb_checks": {},
            "smoke_score": 0,
            "correctness_state": "UNVERIFIED"
        },
        "rtlStructure": None,
        "synthesisEstimate": None,
        "floorplanEstimate": None,
        "placementEstimate": None,
        "timingEstimate": None,
        "congestionEstimate": None,
        "powerEstimate": None,
        "inference": None,
        "synthesis": None,
        "floorplan": None,
        "placement": None,
        "timing": None,
        "routing": None,
        "power": None,
        "why": {},
        "warnings": [],
        "explanations": {},
        "replication": {},
        "stages": []
    }

    def add_stage(name: str, status: str, detail: str):
        result["stages"].append({
            "name": name,
            "status": status,
            "detail": detail
        })

    # 1. PARSING & COMPILATION
    add_stage("PARSING", "RUNNING", "Parsing user RTL source code...")
    if not rtl_code:
        result["status"] = "ERROR"
        result["compile"]["status"] = "FAIL"
        result["compile"]["errors"].append("No RTL code provided. Please enter Verilog or SystemVerilog code.")
        add_stage("PARSING", "FAIL", "No code entered.")
        result["elapsed_ms"] = int((time.time() - start_time) * 1000)
        return result

    rtl_ast = parse_verilog(rtl_code)
    tb_ast = parse_verilog(tb_code) if tb_code else None

    # Syntax Errors
    syntax_errors = [e["message"] for e in rtl_ast.syntax_errors]
    if syntax_errors:
        result["status"] = "COMPILE_ERROR"
        result["compile"]["status"] = "FAIL"
        result["compile"]["errors"].extend(syntax_errors)
        result["simulation"]["reason"] = "Compilation failed due to syntax errors."
        result["verification"]["lint_summary"] = {
            "total_issues": len(syntax_errors),
            "errors_count": len(syntax_errors),
            "warnings_count": 0,
            "quality_score": 0,
            "status": "FAIL",
            "issues": [{"category": "Syntax", "severity": "ERROR", "message": msg, "line": 1, "col": 1} for msg in syntax_errors]
        }
        result["verification"]["lint_issues"] = result["verification"]["lint_summary"]["issues"]
        add_stage("PARSING", "FAIL", f"{len(syntax_errors)} syntax error(s) detected.")
        add_stage("COMPILING", "SKIPPED", "Skipped due to syntax errors.")
        add_stage("SIMULATION", "SKIPPED", "Skipped due to compilation failure.")
        add_stage("PHYSICAL ESTIMATION", "SKIPPED", "Physical estimation skipped because RTL failed compilation.")
        result["elapsed_ms"] = int((time.time() - start_time) * 1000)
        return result

    if not rtl_ast.modules:
        result["status"] = "COMPILE_ERROR"
        result["compile"]["status"] = "FAIL"
        result["compile"]["errors"].append("No 'module ... endmodule' declaration found in RTL.")
        add_stage("PARSING", "FAIL", "No modules found.")
        result["elapsed_ms"] = int((time.time() - start_time) * 1000)
        return result

    top_module = rtl_ast.modules[0]
    result["top_module"] = top_module.name
    result["compile"]["modules"] = [m.name for m in rtl_ast.modules]
    add_stage("PARSING", "PASS", f"Parsed module '{top_module.name}'.")

    # 2. STATIC RTL ANALYSIS (LINTING)
    add_stage("LINTING", "RUNNING", "Checking drivers, latches, widths, sensitivity...")
    analyzer = StaticAnalyzer(rtl_ast)
    lint_issues = analyzer.analyze()
    lint_summary = analyzer.get_summary()

    result["verification"]["lint_summary"] = lint_summary
    result["verification"]["lint_issues"] = lint_summary.get("issues", [])

    for iss in lint_issues:
        if iss.severity == "ERROR":
            result["compile"]["errors"].append(f"[Line {iss.line}] {iss.category}: {iss.message}")
        else:
            result["compile"]["warnings"].append(f"[Line {iss.line}] {iss.category}: {iss.message}")
            result["warnings"].append(f"[Line {iss.line}] {iss.category}: {iss.message}")

    if lint_summary["errors_count"] > 0:
        result["compile"]["status"] = "FAIL"
        add_stage("LINTING", "FAIL", f"{lint_summary['errors_count']} critical lint error(s).")
    else:
        add_stage("LINTING", "PASS", f"RTL Quality: {lint_summary['quality_score']}% ({lint_summary['warnings_count']} warnings).")

    # 3. REAL TESTBENCH SIMULATION
    add_stage("SIMULATING", "RUNNING", "Running user testbench simulation...")
    tb_module = None
    if tb_ast and tb_ast.modules:
        # Find testbench module (either starts with tb_ or has no ports or has initial block)
        for m in tb_ast.modules:
            if m.name != top_module.name or len(tb_ast.modules) == 1:
                tb_module = m
                break

    if tb_module:
        sim = UserTBSimulator(top_module, tb_module)
        sim_res = sim.run()

        result["simulation"] = {
            "executed": sim_res["executed"],
            "exit_code": sim_res["exit_code"],
            "duration_ms": sim_res["duration_ms"],
            "simulation_time_units": sim_res.get("simulation_time_units", 0),
            "stdout": sim_res["stdout"],
            "stdout_lines": sim_res["stdout_lines"],
            "checks_passed": sim_res["checks_passed"],
            "checks_failed": sim_res["checks_failed"],
            "reason": ""
        }

        is_compile_pass = result["compile"]["status"] == "PASS"
        sim_executed = sim_res["executed"]
        sim_exit_code = sim_res["exit_code"]
        checks_passed = sim_res.get("checks_passed", 0)
        checks_failed = sim_res.get("checks_failed", 0)
        self_checking = sim_res.get("self_checking", False)
        tb_q = sim_res.get("tb_quality", {})
        outputs_observed = tb_q.get("outputs_observed", False)
        clk_ok = tb_q.get("clock_present", False)
        rst_ok = tb_q.get("reset_tested", False)
        inps_ok = tb_q.get("inputs_driven", False)
        tb_activity_pass = clk_ok and rst_ok and inps_ok

        # Determine evidence-based correctness_state
        if not is_compile_pass or (sim_executed and sim_exit_code != 0) or checks_failed > 0:
            correctness_state = "FAILED"
        elif not sim_executed:
            correctness_state = "UNVERIFIED"
        elif self_checking and checks_passed > 0 and checks_failed == 0:
            correctness_state = "VERIFIED"
        elif outputs_observed:
            correctness_state = "NOT PROVEN"
        else:
            correctness_state = "UNVERIFIED"

        # Compute smoke score (0 - 100)
        score = 0
        if is_compile_pass: score += 20
        if sim_executed and sim_exit_code == 0: score += 20
        if tb_activity_pass: score += 20
        if outputs_observed: score += 20
        if self_checking and checks_passed > 0 and checks_failed == 0: score += 20

        tests_executed = (checks_passed + checks_failed) if self_checking else len([l for l in sim_res["stdout_lines"] if l.strip()])
        coverage_estimate = "NOT AVAILABLE"

        deficiencies = []
        if not outputs_observed:
            deficiencies.append("Output Observation: No DUT output signals observed via $display or waveform monitoring.")
        if not self_checking:
            deficiencies.append("Self-Checking Assertions: No automated assertions or expected-vs-actual checks detected. Functional correctness is NOT PROVEN.")
        if not rst_ok and len(top_module.ports) > 0 and any("rst" in p.name.lower() or "reset" in p.name.lower() for p in top_module.ports):
            deficiencies.append("Reset Verification: Reset sequence not thoroughly asserted/deasserted.")
        if not clk_ok and any("clk" in p.name.lower() or "clock" in p.name.lower() for p in top_module.ports):
            deficiencies.append("Clock Generation: Clock toggle not detected.")
        if not inps_ok:
            deficiencies.append("Input Stimuli: No input signals driven into DUT.")

        smoke_items = [
            {
                "name": "1. RTL Compilation",
                "status": "PASS" if is_compile_pass else "FAIL",
                "standard": "RTL parses into valid AST without syntax or critical lint errors."
            },
            {
                "name": "2. Simulation Execution",
                "status": "PASS" if (sim_executed and sim_exit_code == 0) else ("FAIL" if sim_executed else "NOT RUN"),
                "standard": "Testbench stimulus executes in simulator to clean $finish."
            },
            {
                "name": "3. Testbench Activity",
                "status": "PASS" if tb_activity_pass else "INCOMPLETE",
                "standard": "Clock generation, reset sequence, and input stimuli driven into DUT."
            },
            {
                "name": "4. Output Observation",
                "status": "PASS" if outputs_observed else "NOT OBSERVED",
                "standard": "DUT output signals inspected or displayed via $display/$monitor."
            },
            {
                "name": "5. Self-Checking Assertions",
                "status": "PASS" if (self_checking and checks_passed > 0 and checks_failed == 0) else ("FAIL" if checks_failed > 0 else "NOT PROVEN"),
                "standard": "Automated assertions or expected-vs-actual checks prove correctness."
            },
            {
                "name": "6. Functional Correctness",
                "status": correctness_state,
                "standard": "Evidence-based functional verification sign-off."
            }
        ]

        result["verification"]["tb_checks"] = tb_q
        result["verification"]["status"] = correctness_state
        result["verification"]["correctness_state"] = correctness_state
        result["verification"]["smoke_score"] = score
        result["verification"]["overall_score"] = score
        result["verification"]["tests_executed"] = tests_executed
        result["verification"]["coverage_estimate"] = coverage_estimate
        result["verification"]["smoke_items"] = smoke_items
        result["verification"]["tb_eval"] = {
            "score": score,
            "deficiencies": deficiencies,
            "status": correctness_state
        }

        add_stage("SIMULATING", "PASS" if sim_res["exit_code"] == 0 else "FAIL",
                  f"Executed in {sim_res['duration_ms']}ms ({len(sim_res['stdout_lines'])} $display lines captured).")
    else:
        result["simulation"] = {
            "executed": False,
            "exit_code": 0,
            "stdout": "",
            "stdout_lines": [],
            "reason": "Simulation not run: No testbench provided. Enter a testbench with initial begin ... end to simulate."
        }
        is_compile_pass = result["compile"]["status"] == "PASS"
        score = 20 if is_compile_pass else 0
        smoke_items = [
            {"name": "1. RTL Compilation", "status": "PASS" if is_compile_pass else "FAIL", "standard": "RTL parses into valid AST without syntax or critical lint errors."},
            {"name": "2. Simulation Execution", "status": "NOT RUN", "standard": "Testbench stimulus executes in simulator to clean $finish."},
            {"name": "3. Testbench Activity", "status": "NOT RUN", "standard": "Clock generation, reset sequence, and input stimuli driven into DUT."},
            {"name": "4. Output Observation", "status": "NOT OBSERVED", "standard": "DUT output signals inspected or displayed via $display/$monitor."},
            {"name": "5. Self-Checking Assertions", "status": "NOT PROVEN", "standard": "Automated assertions or expected-vs-actual checks prove correctness."},
            {"name": "6. Functional Correctness", "status": "UNVERIFIED", "standard": "Evidence-based functional verification sign-off."}
        ]
        result["verification"]["status"] = "UNVERIFIED"
        result["verification"]["correctness_state"] = "UNVERIFIED"
        result["verification"]["smoke_score"] = score
        result["verification"]["overall_score"] = score
        result["verification"]["tests_executed"] = 0
        result["verification"]["coverage_estimate"] = "NOT AVAILABLE"
        result["verification"]["smoke_items"] = smoke_items
        result["verification"]["tb_checks"] = {
            "clock_present": False,
            "reset_tested": False,
            "dut_instantiated": False,
            "inputs_driven": False,
            "outputs_observed": False,
            "outputs_checked": False,
            "self_checking": False,
            "simulation_ends": False,
            "status": "NOT PROVIDED"
        }
        result["verification"]["tb_eval"] = {
            "score": score,
            "deficiencies": ["No testbench provided."],
            "status": "UNVERIFIED"
        }
        add_stage("SIMULATING", "SKIPPED", "No testbench provided.")

    # IF CRITICAL COMPILE ERROR -> DO NOT RUN PHYSICAL ESTIMATION!
    if result["compile"]["status"] == "FAIL":
        result["status"] = "COMPILE_ERROR"
        add_stage("HARDWARE ESTIMATION", "SKIPPED", "Skipped due to compilation errors.")
        add_stage("PHYSICAL ESTIMATION", "SKIPPED", "Physical estimation skipped because RTL failed compilation.")
        result["elapsed_ms"] = int((time.time() - start_time) * 1000)
        return result

    # 4. HARDWARE STRUCTURE INFERENCE
    add_stage("HARDWARE ESTIMATION", "RUNNING", "Inferring hardware blocks directly from RTL...")
    inferencer = HardwareInferencer(top_module)
    inf_data = inferencer.infer()

    result["rtlStructure"] = {
        "blocks": inf_data["blocks"],
        "fsms": inf_data["fsms"],
        "clock_domains": inf_data["clock_domains"],
        "reset_domains": inf_data["reset_domains"],
        "register_bits": inf_data["register_bits"],
        "adders": inf_data["adders"],
        "multipliers": inf_data["multipliers"],
        "multiplexers": inf_data["multiplexers"],
        "comparators": inf_data["comparators"],
        "logic_gates": inf_data["logic_gates"],
        "schematic": inf_data["schematic"]
    }
    add_stage("HARDWARE ESTIMATION", "PASS",
              f"Inferred: {inf_data['register_bits']} register bits, {inf_data['adders']} adders, {inf_data['logic_gates']} logic gates, {inf_data['multiplexers']} muxes.")

    # 5. PHYSICAL ESTIMATION
    add_stage("PHYSICAL ESTIMATION", "RUNNING", f"Synthesizing to {tech_node} generic CMOS...")
    tech = TechnologyModel(
        node=tech_node,
        core_utilization=core_util,
        aspect_ratio=aspect_ratio,
        clock_target_mhz=clock_mhz,
        routing_layers=routing_layers
    )

    estimator = SynthesisEstimator(inf_data, tech)
    synth_data = estimator.estimate()
    result["synthesisEstimate"] = synth_data

    # Floorplan
    fp_engine = FloorplanEngine(synth_data, tech, top_module)
    fp_data = fp_engine.plan()
    result["floorplanEstimate"] = fp_data

    # Placement
    placer = PlacementEngine(fp_data, synth_data, tech)
    pl_data = placer.place()
    result["placementEstimate"] = pl_data

    # CTS
    cts_synth = CTSSynthesizer(pl_data, fp_data, tech)
    cts_data = cts_synth.synthesize()

    # Routing & Congestion
    router = EstimatedRouter(pl_data, fp_data, tech)
    route_data = router.route()
    result["congestionEstimate"] = {
        "average_congestion_pct": route_data["average_congestion_pct"],
        "peak_congestion_pct": route_data["max_tile_congestion_pct"],
        "drc_risk": route_data["estimated_drc_risk"],
        "total_nets": route_data["estimated_nets"],
        "estimated_nets": route_data["estimated_nets"],
        "wirelength_um": route_data["estimated_total_wirelength_um"],
        "vias": route_data["total_vias_count"],
        "route_segments": route_data["route_segments"],
        "flightlines": route_data["flightlines"],
        "power_mesh": route_data["power_mesh"],
        "congestion_grid": route_data["congestion_grid"]
    }

    # Timing (STA)
    sta = STAEngine(synth_data, tech, cts_data)
    timing_data = sta.analyze()
    result["timingEstimate"] = timing_data

    # Power
    power_eng = PowerAnalyzer(synth_data, route_data, cts_data, tech)
    power_data = power_eng.analyze()
    result["powerEstimate"] = power_data

    # Efficiency
    eff_eng = EfficiencyAnalyzer(synth_data, timing_data, power_data, fp_data, route_data, lint_summary)
    eff_data = eff_eng.analyze()

    # Causal "WHY?" Explanations
    pipeline_snap = {
        "top_module": top_module.name,
        "synthesis": synth_data,
        "floorplan": fp_data,
        "placement": pl_data,
        "cts": cts_data,
        "routing": route_data,
        "timing": timing_data,
        "power": power_data,
        "inference": inf_data
    }
    why_eng = WhyEngine(pipeline_snap)
    result["explanations"] = why_eng.generate_all()

    # Replication scripts
    repl_gen = ReplicationScriptGenerator(top_module.name, tech.node, tech.clock_target_mhz, tech.core_utilization, tech.aspect_ratio)
    result["replication"] = repl_gen.generate_all()

    add_stage("PHYSICAL ESTIMATION", "PASS",
              f"Area: {synth_data['estimated_cell_area_um2']} µm², Cells: {synth_data['total_cells']}, Slack: {timing_data['worst_setup_slack_ns']} ns.")

    result["status"] = "SUCCESS"
    result["elapsed_ms"] = int((time.time() - start_time) * 1000)

    # Pre-render report
    pipeline_snap["verification"] = result["verification"]
    pipeline_snap["efficiency"] = eff_data
    pipeline_snap["why"] = result["explanations"]
    rb = ReportBuilder(pipeline_snap)
    result["report_html"] = rb.generate_html()

    # Canonical aliases so both analyze_project and EDAPipeline.run provide identical top-level keys
    result["inference"] = result["rtlStructure"]
    result["synthesis"] = synth_data
    result["floorplan"] = fp_data
    result["placement"] = pl_data
    result["routing"] = result["congestionEstimate"]
    result["timing"] = timing_data
    result["power"] = power_data
    result["why"] = result["explanations"]

    return result

class EDAPipeline:
    """Wrapper class maintaining compatibility with test suites."""
    def __init__(self, rtl_code: str, tb_code: str = "", tech_node: str = "130nm",
                 core_util: float = 0.70, aspect_ratio: float = 1.0,
                 clock_mhz: float = 100.0, routing_layers: int = 6):
        self.project = {
            "rtl": rtl_code,
            "tb": tb_code,
            "tech_node": tech_node,
            "core_util": core_util,
            "aspect_ratio": aspect_ratio,
            "clock_mhz": clock_mhz,
            "routing_layers": routing_layers
        }

    def run(self) -> Dict[str, Any]:
        res = analyze_project(self.project)
        # Adapt keys for any legacy consumers
        res["inference"] = res.get("rtlStructure") or {}
        res["synthesis"] = res.get("synthesisEstimate") or {}
        res["floorplan"] = res.get("floorplanEstimate") or {}
        res["placement"] = res.get("placementEstimate") or {}
        res["routing"] = res.get("congestionEstimate") or {}
        res["timing"] = res.get("timingEstimate") or {}
        res["power"] = res.get("powerEstimate") or {}
        res["why"] = res.get("explanations") or {}
        # Ensure stages format
        if "stages" in res and res["stages"]:
            for s in res["stages"]:
                if "inputs" not in s: s["inputs"] = "Current RTL"
                if "outputs" not in s: s["outputs"] = s.get("detail", "")
                if "explanation" not in s: s["explanation"] = s.get("detail", "")
        return res
