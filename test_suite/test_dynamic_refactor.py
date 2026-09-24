# Mandatory Dynamic Input-Change Tests (Sections 23 - 28)
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eda.pipeline import analyze_project

def test_dynamic_behavior():
    print("=================================================================")
    print("TESTING DYNAMIC PIPELINE RESPONSE TO CODE CHANGES")
    print("=================================================================")

    # -------------------------------------------------------------
    # TEST 1: Logic Operator Change (AND vs OR)
    # -------------------------------------------------------------
    print("\n--- TEST 1: Operator Change (AND vs OR) ---")
    rtl_and = "module logic_op (input [7:0] a, input [7:0] b, output wire [7:0] y); assign y = a & b; endmodule"
    rtl_or  = "module logic_op (input [7:0] a, input [7:0] b, output wire [7:0] y); assign y = a | b; endmodule"

    res_and = analyze_project({"rtl": rtl_and})
    res_or  = analyze_project({"rtl": rtl_or})

    gate_and = res_and["rtlStructure"]["blocks"][0]["name"]
    gate_or  = res_or["rtlStructure"]["blocks"][0]["name"]
    print(f"RTL 1 (a & b) -> Inferred: {gate_and}")
    print(f"RTL 2 (a | b) -> Inferred: {gate_or}")
    assert "AND" in gate_and, f"Expected AND gate, got {gate_and}"
    assert "OR" in gate_or, f"Expected OR gate, got {gate_or}"
    print("[PASS] TEST 1 PASSED: Hardware interpretation correctly changed from AND to OR!")

    # -------------------------------------------------------------
    # TEST 2: Width Change (4-bit vs 32-bit)
    # -------------------------------------------------------------
    print("\n--- TEST 2: Bit-Width Change (4-bit vs 32-bit Adder) ---")
    rtl_w4  = "module add_w (input [3:0] a, input [3:0] b, output wire [3:0] y); assign y = a + b; endmodule"
    rtl_w32 = "module add_w (input [31:0] a, input [31:0] b, output wire [31:0] y); assign y = a + b; endmodule"

    res_w4  = analyze_project({"rtl": rtl_w4})
    res_w32 = analyze_project({"rtl": rtl_w32})

    cells_4 = res_w4["synthesisEstimate"]["total_cells"]
    cells_32 = res_w32["synthesisEstimate"]["total_cells"]
    area_4 = res_w4["synthesisEstimate"]["cell_area_um2"]
    area_32 = res_w32["synthesisEstimate"]["cell_area_um2"]

    print(f"4-bit Adder  -> Cells: {cells_4}, Cell Area: {area_4} um2")
    print(f"32-bit Adder -> Cells: {cells_32}, Cell Area: {area_32} um2")
    assert cells_32 > cells_4 * 5, f"32-bit adder ({cells_32}) should have ~8x cells of 4-bit ({cells_4})"
    assert area_32 > area_4 * 5, f"32-bit adder area ({area_32}) should be ~8x of 4-bit ({area_4})"
    print("[PASS] TEST 2 PASSED: Width change directly quadrupled/scaled cells and area!")

    # -------------------------------------------------------------
    # TEST 3: Register Count Change (4 vs 32 registers)
    # -------------------------------------------------------------
    print("\n--- TEST 3: Register Count Change (4-bit vs 32-bit Register) ---")
    rtl_r4 = """module reg_cnt (input clk, input rst, input [3:0] d, output reg [3:0] q);
        always @(posedge clk) begin if (rst) q <= 4'd0; else q <= d; end
    endmodule"""
    rtl_r32 = """module reg_cnt (input clk, input rst, input [31:0] d, output reg [31:0] q);
        always @(posedge clk) begin if (rst) q <= 32'd0; else q <= d; end
    endmodule"""

    res_r4 = analyze_project({"rtl": rtl_r4})
    res_r32 = analyze_project({"rtl": rtl_r32})

    regs_4 = res_r4["rtlStructure"]["register_bits"]
    regs_32 = res_r32["rtlStructure"]["register_bits"]
    core_w4 = res_r4["floorplanEstimate"]["core"]["width_um"]
    core_w32 = res_r32["floorplanEstimate"]["core"]["width_um"]

    print(f"4-bit Reg  -> Registers: {regs_4}, Core Width: {core_w4} um")
    print(f"32-bit Reg -> Registers: {regs_32}, Core Width: {core_w32} um")
    assert regs_4 == 4, f"Expected 4 registers, got {regs_4}"
    assert regs_32 == 32, f"Expected 32 registers, got {regs_32}"
    assert core_w32 > core_w4 * 2, f"Core width should substantially expand from {core_w4} to {core_w32}"
    print("[PASS] TEST 3 PASSED: Register count and floorplan dimensions dynamically updated!")

    # -------------------------------------------------------------
    # TEST 4: Broken RTL -> Compile Failed & Physical Estimation Skipped
    # -------------------------------------------------------------
    print("\n--- TEST 4: Broken RTL Handling ---")
    rtl_broken = "module broken (input a, output wire y) assign y = ; endmodule" # syntax error
    res_broken = analyze_project({"rtl": rtl_broken})

    print(f"Compile Status: {res_broken['compile']['status']}")
    print(f"Simulation Executed: {res_broken['simulation']['executed']} (Reason: {res_broken['simulation']['reason']})")
    print(f"Physical Estimation: {res_broken['synthesisEstimate']}")
    assert res_broken["compile"]["status"] == "FAIL", "Compile should fail on syntax error"
    assert res_broken["simulation"]["executed"] == False, "Simulation should NOT run on compile failure"
    assert res_broken["synthesisEstimate"] is None, "Physical estimation MUST be None on compile failure"
    print("[PASS] TEST 4 PASSED: Broken RTL stops downstream analysis; no fake physical results!")

    # -------------------------------------------------------------
    # TEST 5: Valid RTL with Incomplete Testbench
    # -------------------------------------------------------------
    print("\n--- TEST 5: Valid RTL with Incomplete Testbench ---")
    tb_incomplete = """module tb_inc;
        reg clk;
        wire [3:0] q;
        // Never drives reset or checks output
        initial begin clk = 0; #10; $finish; end
    endmodule"""
    res_incomp = analyze_project({"rtl": rtl_r4, "tb": tb_incomplete})

    tb_status = res_incomp["verification"]["tb_checks"]["status"]
    print(f"TB Status: {tb_status}")
    print(f"Reset Tested: {res_incomp['verification']['tb_checks']['reset_tested']}")
    assert tb_status != "VALID", f"Expected INCOMPLETE or INVALID, got {tb_status}"
    assert res_incomp["verification"]["tb_checks"]["reset_tested"] == False, "Reset was not tested"
    print("[PASS] TEST 5 PASSED: Incomplete testbench correctly flagged as INCOMPLETE!")

    # -------------------------------------------------------------
    # TEST 6: Two Completely Different Designs (Counter vs 32-bit ALU)
    # -------------------------------------------------------------
    print("\n--- TEST 6: Two Completely Different Designs (Counter vs ALU) ---")
    rtl_counter = """module simple_counter(input clk, input rst, output reg [3:0] count);
        always @(posedge clk) begin if (rst) count <= 0; else count <= count + 1; end
    endmodule"""
    rtl_alu = """module big_alu(input [1:0] op, input [31:0] a, input [31:0] b, output reg [31:0] y);
        always @(*) begin
            case (op)
                2'b00: y = a + b;
                2'b01: y = a - b;
                2'b10: y = a & b;
                default: y = a | b;
            endcase
        end
    endmodule"""

    res_counter = analyze_project({"rtl": rtl_counter})
    res_alu = analyze_project({"rtl": rtl_alu})

    c_cells = res_counter["synthesisEstimate"]["total_cells"]
    c_area = res_counter["synthesisEstimate"]["cell_area_um2"]
    alu_cells = res_alu["synthesisEstimate"]["total_cells"]
    alu_area = res_alu["synthesisEstimate"]["cell_area_um2"]

    print(f"Counter -> Cells: {c_cells}, Area: {c_area} um2")
    print(f"ALU     -> Cells: {alu_cells}, Area: {alu_area} um2")
    assert c_cells != alu_cells, "Cell count must be completely different"
    assert c_area != alu_area, "Area must be completely different"
    assert alu_cells > c_cells * 2, f"32-bit ALU ({alu_cells}) should be much larger than 4-bit counter ({c_cells})"
    print("[PASS] TEST 6 PASSED: Entire result visibly and substantially changes between designs!")

    print("\n=================================================================")
    print("ALL 6 DYNAMIC REFACTOR ACCEPTANCE TESTS PASSED SUCCESSFULLY!")
    print("=================================================================\n")

if __name__ == "__main__":
    test_dynamic_behavior()
