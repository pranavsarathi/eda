# Final Acceptance Test Suite: Proving Real Analysis Pipeline Correctness
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eda.pipeline import analyze_project

def run_acceptance_tests():
    print("=================================================================")
    print("FINAL ACCEPTANCE CRITERIA VERIFICATION (TESTS A - F)")
    print("=================================================================\n")

    # -------------------------------------------------------------
    # TEST A: Change RTL -> Result changes appropriately
    # -------------------------------------------------------------
    print("--- TEST A: RTL Operator Change (a + b vs a & b) ---")
    rtl_add = "module test(input [3:0] a, input [3:0] b, output [3:0] y); assign y = a + b; endmodule"
    rtl_and = "module test(input [3:0] a, input [3:0] b, output [3:0] y); assign y = a & b; endmodule"

    res_add = analyze_project({"rtl": rtl_add, "tb": ""})
    res_and = analyze_project({"rtl": rtl_and, "tb": ""})

    print(f"RTL A (a + b) -> Inferred Adders: {res_add['rtlStructure']['adders']}, Total Cells: {res_add['synthesisEstimate']['total_cells']}, Delay: {res_add['timingEstimate']['critical_path_delay_ns']}ns")
    print(f"RTL B (a & b) -> Inferred Adders: {res_and['rtlStructure']['adders']}, Total Cells: {res_and['synthesisEstimate']['total_cells']}, Delay: {res_and['timingEstimate']['critical_path_delay_ns']}ns")

    assert res_add['rtlStructure']['adders'] == 1, "Add RTL should infer 1 adder"
    assert res_and['rtlStructure']['adders'] == 0, "And RTL should infer 0 adders"
    assert res_add['synthesisEstimate']['estimated_cell_area_um2'] > 2.0 * res_and['synthesisEstimate']['estimated_cell_area_um2'], "Adder area must be > 2x larger than AND gate area"
    assert res_add['timingEstimate']['critical_path_delay_ns'] > res_and['timingEstimate']['critical_path_delay_ns'], "Adder delay must be larger than AND gate delay"
    assert "FA_X1" in res_add['synthesisEstimate']['cell_counts'], "Adder must use FA_X1 cells"
    assert "AND2_X1" in res_and['synthesisEstimate']['cell_counts'], "AND logic must use AND2_X1 cells"
    print("[PASS] TEST A PASSED: Modifying RTL directly changes inferred hardware, cell area, and delay!\n")

    # -------------------------------------------------------------
    # TEST B: Change testbench -> Simulation output changes
    # -------------------------------------------------------------
    print("--- TEST B: Testbench Stimulus Change (input=0 vs input=1) ---")
    rtl_buf = "module my_buf(input a, output wire y); assign y = a; endmodule"
    tb_0 = """module tb;
    reg a; wire y; my_buf dut(a,y);
    initial begin
        a = 0; #5;
        $display("OUTPUT_CHECK: y=%0d", y);
        $finish;
    end
endmodule"""
    tb_1 = """module tb;
    reg a; wire y; my_buf dut(a,y);
    initial begin
        a = 1; #5;
        $display("OUTPUT_CHECK: y=%0d", y);
        $finish;
    end
endmodule"""

    res_tb0 = analyze_project({"rtl": rtl_buf, "tb": tb_0})
    res_tb1 = analyze_project({"rtl": rtl_buf, "tb": tb_1})

    stdout0 = res_tb0["simulation"]["stdout"].strip()
    stdout1 = res_tb1["simulation"]["stdout"].strip()

    print(f"TB with a=0 captured stdout: '{stdout0}'")
    print(f"TB with a=1 captured stdout: '{stdout1}'")

    assert "OUTPUT_CHECK: y=0" in stdout0, "TB0 must output y=0"
    assert "OUTPUT_CHECK: y=1" in stdout1, "TB1 must output y=1"
    assert stdout0 != stdout1, "Stdout must dynamically change with testbench changes"
    print("[PASS] TEST B PASSED: Changing testbench stimulus changes actual simulator stdout!\n")

    # -------------------------------------------------------------
    # TEST C: Change register width -> Hardware and physical estimates change
    # -------------------------------------------------------------
    print("--- TEST C: Register Width Scaling (reg [3:0] vs reg [31:0]) ---")
    rtl_reg4 = """module reg_test(input clk, input rst_n, input [3:0] d, output reg [3:0] q);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) q <= 4'd0;
        else q <= d;
    end
endmodule"""
    rtl_reg32 = """module reg_test(input clk, input rst_n, input [31:0] d, output reg [31:0] q);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) q <= 32'd0;
        else q <= d;
    end
endmodule"""

    res_reg4 = analyze_project({"rtl": rtl_reg4, "tb": ""})
    res_reg32 = analyze_project({"rtl": rtl_reg32, "tb": ""})

    r4_bits = res_reg4["rtlStructure"]["register_bits"]
    r32_bits = res_reg32["rtlStructure"]["register_bits"]
    r4_area = res_reg4["synthesisEstimate"]["estimated_cell_area_um2"]
    r32_area = res_reg32["synthesisEstimate"]["estimated_cell_area_um2"]
    r4_core_w = res_reg4["floorplanEstimate"]["core"]["width_um"]
    r32_core_w = res_reg32["floorplanEstimate"]["core"]["width_um"]

    print(f"4-bit Reg  -> Bits: {r4_bits}, Cell Area: {r4_area:.2f} um2, Core Width: {r4_core_w:.2f} um")
    print(f"32-bit Reg -> Bits: {r32_bits}, Cell Area: {r32_area:.2f} um2, Core Width: {r32_core_w:.2f} um")

    assert r4_bits == 4 and r32_bits == 32, "Register bits must be 4 and 32"
    assert r32_area >= 6.0 * r4_area, "32-bit register area must scale by ~8x"
    assert r32_core_w > r4_core_w, "Core width must expand for 32-bit register"
    print("[PASS] TEST C PASSED: Register width scaling directly scales bits, cell area, and core geometry!\n")

    # -------------------------------------------------------------
    # TEST D: Syntax error -> Analysis stops and physical results blocked
    # -------------------------------------------------------------
    print("--- TEST D: Broken RTL / Syntax Error Handling ---")
    broken_rtl = """module broken(
input a,
output y

assign y = a;"""

    res_broken = analyze_project({"rtl": broken_rtl, "tb": ""})

    print(f"Broken RTL Status: {res_broken['status']}")
    print(f"Compile Status:    {res_broken['compile']['status']}")
    print(f"Errors Caught:     {res_broken['compile']['errors']}")
    print(f"Floorplan Estimate is None: {res_broken['floorplanEstimate'] is None}")
    print(f"Placement Estimate is None: {res_broken['placementEstimate'] is None}")
    print(f"Timing Estimate is None:    {res_broken['timingEstimate'] is None}")

    assert res_broken["compile"]["status"] == "FAIL", "Compile status must be FAIL"
    assert res_broken["floorplanEstimate"] is None, "Floorplan must be None on syntax error"
    assert res_broken["placementEstimate"] is None, "Placement must be None on syntax error"
    assert res_broken["timingEstimate"] is None, "Timing must be None on syntax error"
    print("[PASS] TEST D PASSED: Broken RTL halts pipeline; physical estimation blocked with NO fake results!\n")

    # -------------------------------------------------------------
    # TEST E: Technology / Utilization change -> Physical estimate changes
    # -------------------------------------------------------------
    print("--- TEST E: Utilization Parameter Scaling (70% vs 90%) ---")
    counter_rtl = """module ctr(input clk, input rst_n, output reg [7:0] count);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) count <= 8'd0;
        else count <= count + 1'b1;
    end
endmodule"""

    res_util70 = analyze_project({"rtl": counter_rtl, "tb": "", "core_util": 0.70})
    res_util90 = analyze_project({"rtl": counter_rtl, "tb": "", "core_util": 0.90})

    core70 = res_util70["floorplanEstimate"]["core"]
    core90 = res_util90["floorplanEstimate"]["core"]

    print(f"Core at 70% Util -> Area: {core70['area_um2']:.2f} um2, Width: {core70['width_um']:.2f} um, Util: {core70['utilization_pct']}%")
    print(f"Core at 90% Util -> Area: {core90['area_um2']:.2f} um2, Width: {core90['width_um']:.2f} um, Util: {core90['utilization_pct']}%")

    assert core70["area_um2"] > core90["area_um2"], "70% utilization core area must be larger than 90% core area"
    assert core70["utilization_pct"] < core90["utilization_pct"], "Utilization percentage must be strictly different"
    print("[PASS] TEST E PASSED: Changing utilization directly recalculates core geometry and density!\n")

    # -------------------------------------------------------------
    # TEST F: Two completely different designs -> Visibly different results
    # -------------------------------------------------------------
    print("--- TEST F: Two Distinct Designs (Counter vs Vending Machine) ---")
    vending_rtl = """module vending_machine (
    input clk, input rst_n, input [1:0] coin, output reg dispense, output reg [1:0] change
);
    reg [4:0] total;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin total <= 0; dispense <= 0; change <= 0; end
        else begin
            dispense <= 0; change <= 0;
            if (coin == 2'b01) total <= total + 5;
            else if (coin == 2'b10) total <= total + 10;
            else if (coin == 2'b11) total <= total + 25;
            if (total >= 20) begin dispense <= 1; total <= 0; end
        end
    end
endmodule"""

    res_vending = analyze_project({"rtl": vending_rtl, "tb": ""})
    res_counter = analyze_project({"rtl": counter_rtl, "tb": ""})

    print(f"Counter -> Cells: {res_counter['synthesisEstimate']['total_cells']}, Area: {res_counter['floorplanEstimate']['core']['area_um2']:.2f} um2")
    print(f"Vending -> Cells: {res_vending['synthesisEstimate']['total_cells']}, Area: {res_vending['floorplanEstimate']['core']['area_um2']:.2f} um2")

    assert res_vending["top_module"] == "vending_machine"
    assert res_counter["top_module"] == "ctr"
    assert res_vending["synthesisEstimate"]["total_cells"] != res_counter["synthesisEstimate"]["total_cells"]
    print("[PASS] TEST F PASSED: Two distinct designs yield completely distinct hardware and physical structures!\n")

    print("=================================================================")
    print("ALL ACCEPTANCE TESTS (A - F) PASSED 100% SUCCESSFULLY!")
    print("=================================================================")

if __name__ == "__main__":
    run_acceptance_tests()
