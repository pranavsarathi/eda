import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eda.parser.verilog_parser import parse_verilog
from eda.hardware_inference.inferencer import HardwareInferencer
from eda.analyzer.static_analyzer import StaticAnalyzer
from eda.pipeline import analyze_project

golden_rtl = """module vending_machine (
    input clk,
    input rst,
    input [1:0] coin,
    output reg dispense,
    output reg [1:0] change
);
    localparam S0       = 3'b000;
    localparam S5       = 3'b001;
    localparam S10      = 3'b010;
    localparam DISPENSE = 3'b011;
    localparam CHANGE   = 3'b100;

    reg [2:0] state, next_state;

    // State register (synchronous reset)
    always @(posedge clk) begin
        if (rst)
            state <= S0;
        else
            state <= next_state;
    end

    // Next-state logic
    always @(*) begin
        case (state)
            S0: begin
                if (coin == 2'b01) next_state = S5;
                else if (coin == 2'b10) next_state = S10;
                else next_state = S0;
            end
            S5: begin
                if (coin == 2'b01) next_state = S10;
                else if (coin == 2'b10) next_state = DISPENSE;
                else next_state = S5;
            end
            S10: begin
                if (coin == 2'b01) next_state = DISPENSE;
                else if (coin == 2'b10) next_state = CHANGE;
                else next_state = S10;
            end
            DISPENSE: next_state = S0;
            CHANGE:   next_state = S0;
            default:  next_state = S0;
        endcase
    end

    // Output logic (Moore outputs)
    always @(*) begin
        dispense = 1'b0;
        change = 2'b00;
        case (state)
            DISPENSE: begin
                dispense = 1'b1;
                change = 2'b00;
            end
            CHANGE: begin
                dispense = 1'b1;
                change = 2'b01;
            end
            default: begin
                dispense = 1'b0;
                change = 2'b00;
            end
        endcase
    end
endmodule"""

golden_tb = """module tb_vending_machine;
    reg clk, rst;
    reg [1:0] coin;
    wire dispense;
    wire [1:0] change;

    vending_machine dut (
        .clk(clk), .rst(rst), .coin(coin),
        .dispense(dispense), .change(change)
    );

    always #5 clk = ~clk;

    initial begin
        clk = 0; rst = 1; coin = 2'b00;
        #15 rst = 0;
        $display("[TB] Reset released.");

        // 5 + 10 -> DISPENSE
        #10 coin = 2'b01; #10 coin = 2'b00;
        #10 coin = 2'b10; #10 coin = 2'b00;
        #10 $display("[TB] After 5+10: state dispense=%b change=%b", dispense, change);

        // 10 + 5 -> DISPENSE
        #10 coin = 2'b10; #10 coin = 2'b00;
        #10 coin = 2'b01; #10 coin = 2'b00;
        #10 $display("[TB] After 10+5: state dispense=%b change=%b", dispense, change);

        // 10 + 10 -> CHANGE
        #10 coin = 2'b10; #10 coin = 2'b00;
        #10 coin = 2'b10; #10 coin = 2'b00;
        #10 $display("[TB] After 10+10: state dispense=%b change=%b", dispense, change);

        // 5 + 5 + 5 -> DISPENSE (wait S0 -> S5 -> S10 -> DISPENSE)
        #10 coin = 2'b01; #10 coin = 2'b00;
        #10 coin = 2'b01; #10 coin = 2'b00;
        #10 coin = 2'b01; #10 coin = 2'b00;
        #10 $display("[TB] After 5+5+5: state dispense=%b change=%b", dispense, change);

        #20 $finish;
    end
endmodule"""

def test_vending():
    ast = parse_verilog(golden_rtl)
    top = ast.modules[0]

    # Test static analyzer
    analyzer = StaticAnalyzer(ast)
    lint_issues = analyzer.analyze()
    print("--- LINT ISSUES ---")
    for iss in lint_issues:
        print(f"[{iss.severity}] {iss.category}: {iss.message}")

    # Test hardware inferencer
    inferencer = HardwareInferencer(top)
    inf = inferencer.infer()
    print("\n--- INFERENCE RESULTS ---")
    print("Clock domains:", inf["clock_domains"])
    print("Reset domains:", inf["reset_domains"])
    print("FSM count:", inf["fsms_count"])
    for idx, fsm in enumerate(inf["fsms"]):
        print(f"  FSM {idx}: reg={fsm['state_reg']}, states={fsm['states']}")
    print("Register bits:", inf["register_bits"])
    print("Blocks:")
    for b in inf["blocks"]:
        print(f"  {b['block_type']}: {b['name']} (width={b['width']}, details={b['details']})")

    # Test pipeline result
    res = analyze_project({"rtl": golden_rtl, "tb": golden_tb})
    print("\n--- PIPELINE RESULT ---")
    print("Status:", res["status"])
    print("Verification correctness_state:", res["verification"]["correctness_state"])
    print("Verification tb_checks:", res["verification"]["tb_checks"])
    print("Synthesis total cells:", res["synthesisEstimate"]["total_cells"])
    print("Synthesis cell counts:", res["synthesisEstimate"]["cell_counts"])
    print("Simulation exit code:", res["simulation"]["exit_code"])
    print("Simulation stdout:\n" + res["simulation"]["stdout"].strip())

if __name__ == "__main__":
    test_vending()
