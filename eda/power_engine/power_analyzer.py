# Power Analysis & Energy Dissipation Estimator
from typing import Dict, List, Any
from eda.technology_model.tech_library import TechnologyModel

class PowerAnalyzer:
    def __init__(self, synthesis_data: Dict[str, Any], routing_data: Dict[str, Any],
                 cts_data: Dict[str, Any], tech: TechnologyModel):
        self.synth = synthesis_data
        self.routing = routing_data
        self.cts = cts_data
        self.tech = tech

    def analyze(self) -> Dict[str, Any]:
        vdd = self.tech.info["vdd"]
        f_clk_hz = self.tech.clock_target_mhz * 1e6
        total_cells = self.synth.get("total_cells", 50)
        seq_cells = self.synth.get("sequential_elements", 10)
        comb_cells = self.synth.get("combinational_cells", 40)
        total_wire_um = self.routing.get("estimated_total_wirelength_um", 1000.0)
        cts_buffers = self.cts.get("buffer_count", 2)

        # 1. Switching Activity factor alpha (typically 0.10 to 0.15 for digital logic)
        switching_activity = 0.12

        # 2. Dynamic Wire Switching Power: P_wire = 0.5 * C_wire * Vdd^2 * f_clk * alpha
        # Wire cap in fF per micron -> convert to Farads
        wire_cap_f = (total_wire_um * self.tech.info["wire_cap_ff_per_um"]) * 1e-15
        p_wire_w = 0.5 * wire_cap_f * (vdd ** 2) * f_clk_hz * switching_activity
        p_wire_mw = p_wire_w * 1000.0

        # 3. Internal Cell Dynamic Power: sum(E_int * f_clk * alpha)
        # Average dynamic energy per cell in fJ -> convert to Joules
        avg_dyn_energy_j = 2.5 * self.tech.info["scale_factor"] * 1e-15
        p_internal_w = total_cells * avg_dyn_energy_j * f_clk_hz * switching_activity
        p_internal_mw = p_internal_w * 1000.0

        p_dynamic_total_mw = round(p_wire_mw + p_internal_mw, 3)

        # 4. Clock Tree Power: P_clock = C_clock_total * Vdd^2 * f_clk
        # Clock toggles EVERY cycle (alpha = 1.0 or 2 transitions per period)
        clk_wire_um = self.cts.get("clock_path_length_um", 200.0)
        clk_wire_cap_f = (clk_wire_um * self.tech.info["wire_cap_ff_per_um"]) * 1e-15
        clk_buf_cap_f = (cts_buffers * 8.0 * self.tech.info["scale_factor"]) * 1e-15
        clk_sink_cap_f = (seq_cells * 4.5 * self.tech.info["scale_factor"]) * 1e-15
        total_clk_cap_f = clk_wire_cap_f + clk_buf_cap_f + clk_sink_cap_f
        p_clock_w = total_clk_cap_f * (vdd ** 2) * f_clk_hz
        p_clock_mw = round(p_clock_w * 1000.0, 3)

        # 5. Static Leakage Power: P_leakage = Vdd * sum(I_leak_cell)
        # Average leakage per cell in nW
        avg_leakage_nw = 1.2 * (1.0 / max(0.1, self.tech.info["scale_factor"]))
        p_leakage_nw = total_cells * avg_leakage_nw
        p_leakage_uw = round(p_leakage_nw / 1000.0, 3)
        p_leakage_mw = round(p_leakage_uw / 1000.0, 5)

        total_power_mw = round(p_dynamic_total_mw + p_clock_mw + p_leakage_mw, 3)

        # Proportions
        pct_dynamic = round((p_dynamic_total_mw / max(1e-6, total_power_mw)) * 100, 1)
        pct_clock = round((p_clock_mw / max(1e-6, total_power_mw)) * 100, 1)
        pct_leakage = round((p_leakage_mw / max(1e-6, total_power_mw)) * 100, 2)

        return {
            "estimation_label": "ESTIMATED POWER (Pre-Physical Model)",
            "total_power_mw": total_power_mw,
            "dynamic_power_mw": p_dynamic_total_mw,
            "clock_power_mw": p_clock_mw,
            "leakage_power_uw": p_leakage_uw,
            "switching_activity_alpha": switching_activity,
            "supply_voltage_v": vdd,
            "clock_target_mhz": self.tech.clock_target_mhz,
            "breakdown_pct": {
                "dynamic": pct_dynamic,
                "clock": pct_clock,
                "leakage": pct_leakage
            }
        }
