# Design Efficiency Analyzer & Optimization Advisory Engine
from typing import Dict, List, Any

class EfficiencyAnalyzer:
    def __init__(self, synth_data: Dict[str, Any], timing_data: Dict[str, Any],
                 power_data: Dict[str, Any], fp_data: Dict[str, Any],
                 routing_data: Dict[str, Any], lint_data: Dict[str, Any]):
        self.synth = synth_data
        self.timing = timing_data
        self.power = power_data
        self.fp = fp_data
        self.routing = routing_data
        self.lint = lint_data

    def analyze(self) -> Dict[str, Any]:
        optimizations = []

        util = self.fp.get("core", {}).get("utilization_pct", 70.0)
        slack = self.timing.get("worst_setup_slack_ns", 1.0)
        logic_depth = self.synth.get("logic_depth", 4)
        total_cells = self.synth.get("total_cells", 50)
        seq_cells = self.synth.get("sequential_elements", 10)
        comb_cells = self.synth.get("combinational_cells", 40)
        congestion_pct = self.routing.get("average_congestion_pct", 15.0)
        clock_pct = self.power.get("breakdown_pct", {}).get("clock", 30.0)

        # 1. Area Efficiency
        density_tag = "dense (>85%)" if util > 85.0 else ("standard 60-85%" if util >= 60.0 else "sparse (<60%)")
        area_eff = f"Core utilization {util:.1f}% ({density_tag})"
        if util < 60.0:
            optimizations.append({
                "category": "Area",
                "recommendation": "Increase target core utilization from current setting towards 70-75% to reduce die area.",
                "potential_area_reduction": "~10-18% ESTIMATED",
                "confidence": "RULE-BASED (Density < 60%)"
            })

        # 2. Timing Efficiency
        timing_eff = f"Timing {'MET (+' + str(round(slack, 3)) + ' ns margin)' if slack >= 0.0 else 'VIOLATED (' + str(round(slack, 3)) + ' ns slack)'}"
        if slack < 0.0 and logic_depth > 5:
            optimizations.append({
                "category": "Timing",
                "recommendation": f"Pipeline critical datapath: logic depth is currently {logic_depth} stages.",
                "potential_timing_gain": "~30-45% higher Fmax ESTIMATED",
                "confidence": "RULE-BASED (Slack < 0 and Depth > 5)"
            })

        # 3. Power Breakdown
        power_eff = f"Clock power {clock_pct:.1f}%, logic/leakage {max(0.0, 100.0 - clock_pct):.1f}%"
        if clock_pct > 40.0:
            optimizations.append({
                "category": "Power",
                "recommendation": "Implement Clock Gating (ICG cells) on register banks to disable clock toggling during idle cycles.",
                "potential_power_reduction": "~20-35% clock power reduction ESTIMATED",
                "confidence": "RULE-BASED (Clock power > 40%)"
            })

        # 4. Clock Overhead Ratio
        clock_ratio = round((seq_cells / max(1, total_cells)) * 100, 1)
        clock_overhead = f"{clock_ratio:.1f}% sequential ({seq_cells} FFs / {total_cells} cells)"

        # 5. Check Lint issues (inferred latches, unused signals)
        lint_issues = self.lint.get("issues", [])
        latches = [i for i in lint_issues if i.get("category") == "Latch Inference"]
        if latches:
            optimizations.append({
                "category": "RTL Quality",
                "recommendation": f"Eliminate inferred latches ({len(latches)} detected). Replace with synchronous flip-flops or complete all if-else branches.",
                "potential_area_reduction": "Eliminates glitch power and timing uncertainty",
                "confidence": "RULE-BASED (Lint Latch Detection)"
            })

        unused = [i for i in lint_issues if i.get("category") == "Unused Signal"]
        if unused:
            optimizations.append({
                "category": "Area & Netlist",
                "recommendation": f"Remove {len(unused)} unused signals declared in RTL to clean up synthesis netlist.",
                "potential_area_reduction": "~2-4% net count reduction",
                "confidence": "RULE-BASED (Lint Unused Signal)"
            })

        return {
            "area_efficiency": area_eff,
            "timing_efficiency": timing_eff,
            "power_efficiency": power_eff,
            "clock_overhead": clock_overhead,
            "logic_depth": logic_depth,
            "register_count": seq_cells,
            "combinational_count": comb_cells,
            "estimated_congestion_level": f"{congestion_pct:.1f}% avg tile congestion",
            "clock_overhead_pct": clock_ratio,
            "potential_optimizations": optimizations
        }
