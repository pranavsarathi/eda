# Test User Testbench Simulation
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from eda.parser.verilog_parser import parse_verilog
from eda.verifier.simulator import UserTBSimulator

rtl = """
module counter (
    input clk,
    input rst,
    output reg [3:0] q
);
    always @(posedge clk) begin
        if (rst) q <= 4'd0;
        else q <= q + 1'b1;
    end
endmodule
"""

tb = """
module tb;
    reg clk, rst;
    wire [3:0] q;
    counter dut (.clk(clk), .rst(rst), .q(q));
    always #5 clk = ~clk;
    initial begin
        clk = 0; rst = 1;
        $display("TESTBENCH: Starting...");
        #10 rst = 0;
        $display("TESTBENCH: Reset deasserted, q=%d", q);
        #40 $display("TESTBENCH: Count reached q=%d (hex:%h, bin:%b)", q, q, q);
        $finish;
    end
endmodule
"""

ast_rtl = parse_verilog(rtl)
ast_tb = parse_verilog(tb)

sim = UserTBSimulator(ast_rtl.modules[0], ast_tb.modules[0])
res = sim.run()
print("Executed:", res["executed"])
print("Duration:", res["duration_ms"], "ms")
print("Stdout:\n" + res["stdout"])
print("TB Quality:", res["tb_quality"])
