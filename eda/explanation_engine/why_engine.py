# Interactive "WHY?" Explanation Engine
from typing import Dict, List, Any, Optional

class WhyExplanation:
    def __init__(self, key: str, topic: str, result: str, evidence: List[str],
                 reason: str, source_rtl: str, physical_consequence: str,
                 confidence: str = "HIGH"):
        self.key = key
        self.topic = topic
        self.result = result
        self.evidence = evidence
        self.reason = reason
        self.source_rtl = source_rtl
        self.physical_consequence = physical_consequence
        self.confidence = confidence # 'HIGH', 'MEDIUM', 'LOW'

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "topic": self.topic,
            "result": self.result,
            "evidence": self.evidence,
            "reason": self.reason,
            "source_rtl": self.source_rtl,
            "physical_consequence": self.physical_consequence,
            "confidence": self.confidence
        }

class WhyEngine:
    def __init__(self, pipeline_data: Dict[str, Any]):
        self.data = pipeline_data
        self.explanations: Dict[str, WhyExplanation] = {}

    def generate_all(self) -> Dict[str, Any]:
        self.explanations.clear()

        synth = self.data.get("synthesis", {})
        fp = self.data.get("floorplan", {})
        timing = self.data.get("timing", {})
        cts = self.data.get("cts", {})
        routing = self.data.get("routing", {})
        power = self.data.get("power", {})
        inference = self.data.get("inference", {})

        # 1. Why is area what it is?
        area_um2 = synth.get("estimated_cell_area_um2", 0)
        bd = synth.get("breakdown", {})
        reg_cnt = bd.get("registers", 0)
        adder_cnt = bd.get("adders", 0)
        mux_cnt = bd.get("muxes", 0)
        cmp_cnt = bd.get("comparators", 0)

        ev_area = [
            f"Sequential registers: {reg_cnt} flip-flops ({round(synth.get('sequential_area_um2', 0), 1)} µm²)",
            f"Arithmetic adders/subtractors: {adder_cnt} blocks",
            f"Multiplexers: {mux_cnt} cells",
            f"Comparators: {cmp_cnt} cells",
            f"Target technology node: {synth.get('technology_node', '130nm')}"
        ]
        dominant = "registers" if reg_cnt * 30 > adder_cnt * 10 else "arithmetic logic"

        self.explanations["area"] = WhyExplanation(
            key="area",
            topic="Total Cell and Core Area Estimation",
            result=f"Total estimated cell area is {area_um2:,} µm² (Core: {fp.get('core', {}).get('area_um2', 0):,} µm²).",
            evidence=ev_area,
            reason=f"Standard cell area is calculated by mapping RTL structural blocks to calibrated standard cells in the {synth.get('technology_node', '130nm')} generic CMOS library. {dominant.capitalize()} contribute the largest share of silicon footprint.",
            source_rtl=f"Inferred from module declarations and procedural blocks across {len(inference.get('blocks', []))} hardware elements.",
            physical_consequence="Higher area requires larger core boundary dimensions, increasing die package costs and silicon fabrication price per wafer.",
            confidence="HIGH"
        )

        # 2. Why was Clock Tree Synthesis (CTS) performed & Buffers inserted?
        buf_cnt = cts.get("buffer_count", 0)
        sinks = cts.get("clock_sinks", 0)
        levels = cts.get("tree_levels", 0)

        self.explanations["cts"] = WhyExplanation(
            key="cts",
            topic="Clock Tree Buffer Insertion & Topology",
            result=f"Inserted {buf_cnt} clock buffers across {levels} hierarchical tree levels driving {sinks} flip-flop sinks.",
            evidence=[
                f"Clock network drives {sinks} sequential flip-flops.",
                f"Maximum allowable buffer fanout limit is 6 flip-flops per leaf buffer.",
                f"Estimated clock insertion delay is {cts.get('insertion_delay_ns', 0)} ns.",
                f"Estimated clock skew is {cts.get('estimated_skew_ps', 0)} ps."
            ],
            reason="Driving dozens of flip-flop gate capacitances directly from a single clock pin would cause massive transition degradation (slow slew rates) and extreme clock skew across the die. CTS builds an equi-delay buffer tree to synchronize clock arrival times.",
            source_rtl="Inferred from posedge clock sensitivity lists in sequential always blocks.",
            physical_consequence="Controlled clock skew prevents hold-time violations and race conditions on back-to-back registers, while consuming additional power and routing tracks on Metal 4 & Metal 5.",
            confidence="HIGH"
        )

        # 3. Why is Timing / Slack at this value?
        slack_ns = timing.get("worst_setup_slack_ns", 0)
        crit_delay = timing.get("critical_path_delay_ns", 0)
        clk_target = timing.get("clock_target_mhz", 100)
        period = timing.get("clock_period_ns", 10)

        ev_timing = [
            f"Clock target frequency: {clk_target} MHz (Period = {period} ns)",
            f"Critical path arrival delay: {crit_delay} ns",
            f"Setup time + clock skew margin: {round(period - slack_ns - crit_delay, 3)} ns",
            f"Logic depth through combinational path: {synth.get('logic_depth', 0)} gates"
        ]

        if slack_ns >= 0:
            res_timing = f"Positive setup slack (+{slack_ns} ns) achieved at {clk_target} MHz."
            reas_timing = "The cumulative cell intrinsic delays and estimated wire RC delays along the longest datapath are shorter than the allocated clock cycle period."
            conseq_timing = "The synthesized circuit can operate reliably at and slightly above the target clock frequency without timing violations."
        else:
            res_timing = f"Negative setup slack ({slack_ns} ns) timing violation at {clk_target} MHz."
            reas_timing = "The combinational propagation delay through the logic chain exceeds the available clock period minus register setup requirements."
            conseq_timing = "Flip-flops will sample in an indeterminate/metastable state at this frequency. The design must be pipelined or the clock frequency reduced."

        self.explanations["timing"] = WhyExplanation(
            key="timing",
            topic="Static Timing Analysis & Critical Path Slack",
            result=res_timing,
            evidence=ev_timing,
            reason=reas_timing,
            source_rtl=f"Path between startpoint '{timing.get('startpoint', '')}' and endpoint '{timing.get('endpoint', '')}'.",
            physical_consequence=conseq_timing,
            confidence="MEDIUM"
        )

        # 4. Why is Congestion at this level?
        avg_cong = routing.get("average_congestion_pct", 0)
        max_cong = routing.get("max_tile_congestion_pct", 0)
        drc_risk = routing.get("estimated_drc_risk", "LOW")

        self.explanations["congestion"] = WhyExplanation(
            key="congestion",
            topic="Routing Track Demand & Congestion Hotspots",
            result=f"Average routing congestion is {avg_cong}% (Peak tile congestion: {max_cong}%, DRC Risk: {drc_risk}).",
            evidence=[
                f"Total routed signal nets: {routing.get('estimated_nets', 0)}",
                f"Total estimated wirelength: {routing.get('estimated_total_wirelength_um', 0)} µm",
                f"Estimated via count: {routing.get('total_vias_count', 0)} vias",
                f"Core utilization: {fp.get('core', {}).get('utilization_pct', 0)}%"
            ],
            reason="Congestion measures the ratio of required interconnect routing tracks to available routing tracks in Metal 1 through Metal 5 within each GCell tile.",
            source_rtl="Driven by the density of signal connections between placed standard cells and IO boundary ports.",
            physical_consequence="High congestion (>85%) forces detailed routers to detour wires, causing net detours, increased RC delays, and potential Design Rule Check (DRC) shorts and spacing violations.",
            confidence="HIGH"
        )

        # 5. Why are IO ports placed on their specific boundaries?
        self.explanations["ports"] = WhyExplanation(
            key="ports",
            topic="IO Boundary Pin Placement Strategy",
            result="Clock and reset placed on top; data inputs on left; data outputs on right; control on bottom.",
            evidence=[
                "Clock port: Top center for balanced H-tree root access to core center.",
                "Data inputs: Left edge aligns with standard left-to-right digital datapath flow.",
                "Data outputs: Right edge provides straight-through termination from output registers.",
                "Control pins: Bottom edge avoids congestion with high-speed parallel data busses."
            ],
            reason="Structured port assignment mirrors commercial physical design methodology, establishing clean unidirectional data flow and minimizing criss-crossing long global nets.",
            source_rtl="Extracted from module port list direction attributes (input/output).",
            physical_consequence="Significantly reduces half-perimeter wire length (HPWL) and prevents routing congestion bottlenecks at the chip periphery.",
            confidence="HIGH"
        )

        # 6. Why were Filler cells inserted?
        filler_cnt = self.data.get("placement", {}).get("fillers_count", 0)
        self.explanations["fillers"] = WhyExplanation(
            key="fillers",
            topic="Standard Cell Row Filler & Decap Insertion",
            result=f"Inserted {filler_cnt} physical filler cells across unoccupied row sites.",
            evidence=[
                "Standard cell rows have continuous N-well and P-well implants.",
                "VSS and VDD supply rails must maintain unbroken electrical continuity along each row.",
                "Unfilled row sites create DRC well-spacing errors and discontinuous power rails."
            ],
            reason="Standard cells cannot float with blank gaps. Fillers contain power rails, N-well/P-well diffusion continuity, and decoupling capacitors (decap) to stabilize the power grid against dynamic voltage drop (IR-drop).",
            source_rtl="Automatic physical finishing stage after detailed standard-cell placement.",
            physical_consequence="Ensures physical DRC design-rule compliance and photolithographic planarization across all chemical-mechanical polishing (CMP) dummy metal layers.",
            confidence="HIGH"
        )

        return {k: exp.to_dict() for k, exp in self.explanations.items()}
