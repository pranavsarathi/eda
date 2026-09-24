# Static Timing Analysis (STA) & Critical Path Engine
from typing import Dict, List, Any, Optional
from eda.technology_model.tech_library import TechnologyModel

class TimingPathStage:
    def __init__(self, instance_name: str, cell_type: str, stage_type: str,
                 delay_ps: float, fanout: int, slew_ps: float, arrival_ps: float,
                 rtl_line: int = 1):
        self.instance_name = instance_name
        self.cell_type = cell_type
        self.stage_type = stage_type # 'START_REG', 'COMB_LOGIC', 'NET', 'END_REG', 'PORT'
        self.delay_ps = delay_ps
        self.fanout = fanout
        self.slew_ps = slew_ps
        self.arrival_ps = arrival_ps
        self.rtl_line = rtl_line

    def to_dict(self) -> Dict[str, Any]:
        return {
            "instance_name": self.instance_name,
            "cell_type": self.cell_type,
            "stage_type": self.stage_type,
            "delay_ns": round(self.delay_ps / 1000.0, 3),
            "fanout": self.fanout,
            "slew_ps": round(self.slew_ps, 1),
            "arrival_ns": round(self.arrival_ps / 1000.0, 3),
            "rtl_line": self.rtl_line
        }

class STAEngine:
    def __init__(self, synthesis_data: Dict[str, Any], tech: TechnologyModel, cts_data: Dict[str, Any]):
        self.synth = synthesis_data
        self.tech = tech
        self.cts = cts_data
        self.stages: List[TimingPathStage] = []

    def analyze(self) -> Dict[str, Any]:
        self.stages.clear()
        target_freq_mhz = self.tech.clock_target_mhz
        clock_period_ns = round(1000.0 / target_freq_mhz, 3)
        clock_period_ps = clock_period_ns * 1000.0

        # Technology constants
        s = self.tech.info["scale_factor"]
        setup_time_ps = 75.0 * s
        hold_time_ps = 35.0 * s
        clk_skew_ps = self.cts.get("estimated_skew_ps", 30.0)

        # Build critical path stages:
        # Startpoint: REG_START (Clk-to-Q) -> Combinational Gates -> Endpoint: REG_END
        instances = self.synth.get("instances", [])
        seq_insts = [i for i in instances if i.get("function") in ("DFF", "DFFR", "DFFRE")]
        comb_insts = [i for i in instances if i.get("function") not in ("DFF", "DFFR", "DFFRE", "FILL", "CLKBUF")]

        start_inst_name = seq_insts[0]["inst_name"] if seq_insts else "IN_PORT_DATA"
        end_inst_name = seq_insts[-1]["inst_name"] if len(seq_insts) > 1 else (seq_insts[0]["inst_name"] if seq_insts else "OUT_PORT_DATA")

        current_arrival_ps = 0.0

        # Stage 0: Startpoint Flip-Flop (Clk-to-Q delay)
        clk_to_q_ps = round(120.0 * s, 1)
        current_arrival_ps += clk_to_q_ps
        self.stages.append(TimingPathStage(
            instance_name=start_inst_name,
            cell_type="DFFR_X1" if seq_insts else "PORT",
            stage_type="START_REG",
            delay_ps=clk_to_q_ps,
            fanout=2,
            slew_ps=40.0 * s,
            arrival_ps=current_arrival_ps,
            rtl_line=seq_insts[0].get("rtl_line", 1) if seq_insts else 1
        ))

        # Intermediate Combinational Stages along critical path
        # Select representative logic chain (Adder / Mux / Logic gate)
        selected_comb = comb_insts[:min(len(comb_insts), self.synth.get("logic_depth", 5))]
        if not selected_comb:
            selected_comb = [{"inst_name": "U_LOGIC_1", "cell_type": "NAND2_X1", "function": "NAND2", "rtl_line": 1}]

        for idx, c in enumerate(selected_comb):
            # Net wire RC delay
            net_delay_ps = round(25.0 * s + (idx * 4.0 * s), 1)
            current_arrival_ps += net_delay_ps
            self.stages.append(TimingPathStage(
                instance_name=f"net_stage_{idx}",
                cell_type="INTERCONNECT",
                stage_type="NET",
                delay_ps=net_delay_ps,
                fanout=2,
                slew_ps=35.0 * s,
                arrival_ps=current_arrival_ps,
                rtl_line=c.get("rtl_line", 1)
            ))

            # Gate delay
            gate_delay_ps = round(45.0 * s + (idx * 3.5 * s), 1)
            current_arrival_ps += gate_delay_ps
            self.stages.append(TimingPathStage(
                instance_name=c["inst_name"],
                cell_type=c["cell_type"],
                stage_type="COMB_LOGIC",
                delay_ps=gate_delay_ps,
                fanout=2,
                slew_ps=42.0 * s,
                arrival_ps=current_arrival_ps,
                rtl_line=c.get("rtl_line", 1)
            ))

        # Final Net before Endpoint FF
        net_delay_ps = round(20.0 * s, 1)
        current_arrival_ps += net_delay_ps
        self.stages.append(TimingPathStage(
            instance_name="net_to_endpoint",
            cell_type="INTERCONNECT",
            stage_type="NET",
            delay_ps=net_delay_ps,
            fanout=1,
            slew_ps=30.0 * s,
            arrival_ps=current_arrival_ps,
            rtl_line=seq_insts[-1].get("rtl_line", 1) if seq_insts else 1
        ))

        # Endpoint Flip-Flop
        self.stages.append(TimingPathStage(
            instance_name=end_inst_name,
            cell_type="DFFR_X1" if seq_insts else "PORT",
            stage_type="END_REG",
            delay_ps=0.0,
            fanout=1,
            slew_ps=30.0 * s,
            arrival_ps=current_arrival_ps,
            rtl_line=seq_insts[-1].get("rtl_line", 1) if seq_insts else 1
        ))

        total_path_delay_ps = current_arrival_ps
        total_path_delay_ns = round(total_path_delay_ps / 1000.0, 3)

        # Setup Slack Calculation:
        # Required Time = Clock_Period - Setup_Time + Clock_Skew
        required_time_ps = clock_period_ps - setup_time_ps + clk_skew_ps
        slack_ps = required_time_ps - total_path_delay_ps
        slack_ns = round(slack_ps / 1000.0, 3)

        # Hold Slack Calculation:
        # Hold slack = (Clk-to-Q + min_comb_delay) - Hold_time - Skew
        min_comb_ps = 80.0 * s
        hold_slack_ps = (clk_to_q_ps + min_comb_ps) - hold_time_ps - clk_skew_ps
        hold_slack_ns = round(hold_slack_ps / 1000.0, 3)

        has_setup_violation = (slack_ns < 0)
        has_hold_violation = (hold_slack_ns < 0)

        # Fmax achievable
        fmax_mhz = int(round(1000.0 / max(0.4, (total_path_delay_ps + setup_time_ps - clk_skew_ps) / 1000.0)))

        contributors = []
        if has_setup_violation:
            contributors.append("High combinational logic depth along datapath.")
            contributors.append(f"Target clock frequency ({target_freq_mhz} MHz) requires clock period of {clock_period_ns} ns, shorter than datapath delay ({total_path_delay_ns} ns).")
            contributors.append("Accumulated wire RC interconnect delay across multiple metal layers.")

        return {
            "clock_target_mhz": target_freq_mhz,
            "clock_period_ns": clock_period_ns,
            "critical_path_delay_ns": total_path_delay_ns,
            "worst_setup_slack_ns": slack_ns,
            "worst_hold_slack_ns": hold_slack_ns,
            "total_negative_slack_ns": round(min(0.0, slack_ns), 3),
            "estimated_fmax_mhz": fmax_mhz,
            "timing_status": "VIOLATED" if has_setup_violation else "MET",
            "setup_violation": has_setup_violation,
            "hold_violation": has_hold_violation,
            "likely_contributors": contributors,
            "stages": [st.to_dict() for st in self.stages],
            "startpoint": start_inst_name,
            "endpoint": end_inst_name
        }
