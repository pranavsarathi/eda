import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eda.pipeline import analyze_project

def run_audit():
    print("=" * 65)
    print("REPRODUCTION AUDIT: DYNAMIC BEHAVIOR ACROSS PIPELINE")
    print("=" * 65)

    # -----------------------------------------------------------------
    # 1. RTL A vs RTL B
    # -----------------------------------------------------------------
    print("\n--- 1. RTL COMPARISON: (a + b) vs (a & b) ---")
    rtl_a = """module test(
    input [3:0] a,
    input [3:0] b,
    output [3:0] y
);
assign y = a + b;
endmodule"""

    rtl_b = """module test(
    input [3:0] a,
    input [3:0] b,
    output [3:0] y
);
assign y = a & b;
endmodule"""

    res_a = analyze_project({"rtl": rtl_a, "tb": ""})
    res_b = analyze_project({"rtl": rtl_b, "tb": ""})

    metrics_to_compare = [
        ("Inferred Adders", res_a['inference']['adders'], res_b['inference']['adders']),
        ("Inferred Gates", res_a['inference']['logic_gates'], res_b['inference']['logic_gates']),
        ("Total Synth Cells", res_a['synthesis']['total_cells'], res_b['synthesis']['total_cells']),
        ("Cell Area (um2)", res_a['synthesis']['estimated_cell_area_um2'], res_b['synthesis']['estimated_cell_area_um2']),
        ("Critical Path Delay (ns)", res_a['timing']['critical_path_delay_ns'], res_b['timing']['critical_path_delay_ns']),
        ("Estimated Fmax (MHz)", res_a['timing']['estimated_fmax_mhz'], res_b['timing']['estimated_fmax_mhz']),
        ("Core Width (um)", res_a['floorplan']['core']['width_um'], res_b['floorplan']['core']['width_um']),
        ("Core Height (um)", res_a['floorplan']['core']['height_um'], res_b['floorplan']['core']['height_um']),
        ("Core Area (um2)", res_a['floorplan']['core']['area_um2'], res_b['floorplan']['core']['area_um2']),
        ("Placed Cells Count", len(res_a['placement']['cells']), len(res_b['placement']['cells'])),
        ("Congestion Peak %", res_a['routing']['peak_congestion_pct'], res_b['routing']['peak_congestion_pct']),
        ("Routing Wirelength (um)", res_a['routing']['wirelength_um'], res_b['routing']['wirelength_um']),
        ("Total Power (mW)", res_a['power']['total_power_mw'], res_b['power']['total_power_mw'])
    ]

    for label, val_a, val_b in metrics_to_compare:
        status = "DIFFERENT" if val_a != val_b else "IDENTICAL"
        print(f"  {label:<26}: A = {val_a:<10} | B = {val_b:<10} [{status}]")

    assert res_a['inference']['adders'] == 1 and res_b['inference']['adders'] == 0, "Adder count must differ"
    assert res_a['synthesis']['estimated_cell_area_um2'] > 2.0 * res_b['synthesis']['estimated_cell_area_um2'], "Adder area must be > 2x AND area"
    assert res_a['timing']['critical_path_delay_ns'] > res_b['timing']['critical_path_delay_ns'], "Adder delay must be > AND delay"
    assert res_a['floorplan']['core']['area_um2'] > res_b['floorplan']['core']['area_um2'], "Adder core area must be > AND core area"
    print("  => VERIFICATION: RTL modification causally alters inferred hardware, cells, timing, and core area!")

    # -----------------------------------------------------------------
    # 2. Testbench A vs Testbench B
    # -----------------------------------------------------------------
    print("\n--- 2. TESTBENCH COMPARISON (TB A: a=0 vs TB B: a=1) ---")
    tb_a = """module tb;
    reg a; wire y; test_buf dut(a, y);
    initial begin
        a = 0; #10;
        $display("CHECK: a=%b, y=%b", a, y);
        $finish;
    end
    endmodule"""

    tb_b = """module tb;
    reg a; wire y; test_buf dut(a, y);
    initial begin
        a = 1; #10;
        $display("CHECK: a=%b, y=%b", a, y);
        $finish;
    end
    endmodule"""

    rtl_buf = "module test_buf(input a, output wire y); assign y = a; endmodule"

    res_tba = analyze_project({"rtl": rtl_buf, "tb": tb_a})
    res_tbb = analyze_project({"rtl": rtl_buf, "tb": tb_b})

    stdout_a = res_tba['simulation']['stdout'].strip()
    stdout_b = res_tbb['simulation']['stdout'].strip()

    print(f"  TB A stdout: '{stdout_a}'")
    print(f"  TB B stdout: '{stdout_b}'")
    assert "CHECK: a=0, y=0" in stdout_a, "TB A must capture a=0, y=0"
    assert "CHECK: a=1, y=1" in stdout_b, "TB B must capture a=1, y=1"
    assert stdout_a != stdout_b, "Outputs must dynamically differ"
    print("  => VERIFICATION: Changing testbench stimulus directly alters simulator stdout!")

    # -----------------------------------------------------------------
    # 3. 4-bit vs 32-bit register width
    # -----------------------------------------------------------------
    print("\n--- 3. REGISTER WIDTH COMPARISON (4-bit vs 32-bit) ---")
    rtl_4 = "module r(input clk, input [3:0] d, output reg [3:0] q); always @(posedge clk) q <= d; endmodule"
    rtl_32 = "module r(input clk, input [31:0] d, output reg [31:0] q); always @(posedge clk) q <= d; endmodule"

    res_4 = analyze_project({"rtl": rtl_4, "tb": ""})
    res_32 = analyze_project({"rtl": rtl_32, "tb": ""})

    print(f"  4-bit  -> Reg bits: {res_4['inference']['register_bits']}, Total cells: {res_4['synthesis']['total_cells']}, Area: {res_4['floorplan']['core']['area_um2']:.2f} um2")
    print(f"  32-bit -> Reg bits: {res_32['inference']['register_bits']}, Total cells: {res_32['synthesis']['total_cells']}, Area: {res_32['floorplan']['core']['area_um2']:.2f} um2")

    assert res_4['inference']['register_bits'] == 4 and res_32['inference']['register_bits'] == 32, "Register bits must scale 4 to 32"
    assert res_32['floorplan']['core']['area_um2'] > 5.0 * res_4['floorplan']['core']['area_um2'], "32-bit core area must be > 5x 4-bit core area"
    print("  => VERIFICATION: Register bit-width scaling directly expands synthesized hardware and physical core!")

    # -----------------------------------------------------------------
    # 4. Broken RTL test
    # -----------------------------------------------------------------
    print("\n--- 4. BROKEN RTL TEST ---")
    rtl_broken = "module broken (input a output y); assign y = a; endmodule"
    res_broken = analyze_project({"rtl": rtl_broken, "tb": ""})
    print(f"  Compile Status: {res_broken['compile']['status']}")
    print(f"  Floorplan is None: {res_broken['floorplan'] is None}")
    print(f"  Placement is None: {res_broken['placement'] is None}")

    assert res_broken['compile']['status'] == "FAIL", "Broken syntax must fail compile"
    assert res_broken['floorplan'] is None, "Floorplan must be None on compile failure"
    assert res_broken['placement'] is None, "Placement must be None on compile failure"
    assert res_broken['timing'] is None, "Timing must be None on compile failure"
    print("  => VERIFICATION: Broken syntax halts the pipeline with NO fabricated physical data!")

    print("\n" + "=" * 65)
    print("ALL AUDIT VERIFICATIONS PASSED 100%!")
    print("=" * 65)

if __name__ == "__main__":
    run_audit()
