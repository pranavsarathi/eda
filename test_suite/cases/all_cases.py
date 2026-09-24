# 40 Mandatory Educational RTL & Quality Test Cases
from typing import Dict, List, Any

TEST_CASES = [
    # 1. AND gate
    {
        "id": "TC01_AND",
        "name": "2-Input AND Gate",
        "category": "Basic Combinational",
        "is_failure_case": False,
        "rtl": "module and_gate (input a, input b, output wire y); assign y = a & b; endmodule",
        "tb": "module tb; reg a, b; wire y; and_gate dut (a,b,y); initial begin a=0;b=0;#5 a=1;#5 b=1;#5 $finish; end endmodule"
    },
    # 2. OR gate
    {
        "id": "TC02_OR",
        "name": "2-Input OR Gate",
        "category": "Basic Combinational",
        "is_failure_case": False,
        "rtl": "module or_gate (input a, input b, output wire y); assign y = a | b; endmodule",
        "tb": "module tb; reg a, b; wire y; or_gate dut (a,b,y); initial begin a=0;b=0;#5 a=1;#5 $finish; end endmodule"
    },
    # 3. XOR gate
    {
        "id": "TC03_XOR",
        "name": "2-Input XOR Gate",
        "category": "Basic Combinational",
        "is_failure_case": False,
        "rtl": "module xor_gate (input a, input b, output wire y); assign y = a ^ b; endmodule",
        "tb": "module tb; reg a, b; wire y; xor_gate dut (a,b,y); initial begin a=0;b=0;#5 a=1;#5 b=1;#5 $finish; end endmodule"
    },
    # 4. NAND gate
    {
        "id": "TC04_NAND",
        "name": "2-Input NAND Gate",
        "category": "Basic Combinational",
        "is_failure_case": False,
        "rtl": "module nand_gate (input a, input b, output wire y); assign y = ~(a & b); endmodule",
        "tb": "module tb; reg a, b; wire y; nand_gate dut (a,b,y); initial begin a=1;b=1;#5 a=0;#5 $finish; end endmodule"
    },
    # 5. NOR gate
    {
        "id": "TC05_NOR",
        "name": "2-Input NOR Gate",
        "category": "Basic Combinational",
        "is_failure_case": False,
        "rtl": "module nor_gate (input a, input b, output wire y); assign y = ~(a | b); endmodule",
        "tb": "module tb; reg a, b; wire y; nor_gate dut (a,b,y); initial begin a=0;b=0;#5 a=1;#5 $finish; end endmodule"
    },
    # 6. Multiplexer
    {
        "id": "TC06_MUX",
        "name": "4-to-1 Multiplexer",
        "category": "Basic Combinational",
        "is_failure_case": False,
        "rtl": """module mux4 (
    input [3:0] in,
    input [1:0] sel,
    output wire out
);
    assign out = (sel == 2'b00) ? in[0] :
                 (sel == 2'b01) ? in[1] :
                 (sel == 2'b10) ? in[2] : in[3];
endmodule""",
        "tb": "module tb; reg [3:0] in; reg [1:0] sel; wire out; mux4 dut (in,sel,out); initial begin in=4'b1010;sel=0;#5 sel=1;#5 sel=3;#5 $finish; end endmodule"
    },
    # 7. Decoder
    {
        "id": "TC07_DEC",
        "name": "2-to-4 Binary Decoder",
        "category": "Basic Combinational",
        "is_failure_case": False,
        "rtl": """module decoder2to4 (
    input [1:0] in,
    input enable,
    output wire [3:0] out
);
    assign out = enable ? (4'b0001 << in) : 4'b0000;
endmodule""",
        "tb": "module tb; reg [1:0] in; reg enable; wire [3:0] out; decoder2to4 dut (in,enable,out); initial begin enable=1;in=0;#5 in=2;#5 $finish; end endmodule"
    },
    # 8. Encoder
    {
        "id": "TC08_ENC",
        "name": "4-to-2 Priority Encoder",
        "category": "Basic Combinational",
        "is_failure_case": False,
        "rtl": """module priority_encoder4 (
    input [3:0] in,
    output reg [1:0] out,
    output reg valid
);
    always @(*) begin
        valid = 1'b1;
        if (in[3]) out = 2'b11;
        else if (in[2]) out = 2'b10;
        else if (in[1]) out = 2'b01;
        else if (in[0]) out = 2'b00;
        else begin out = 2'b00; valid = 1'b0; end
    end
endmodule""",
        "tb": "module tb; reg [3:0] in; wire [1:0] out; wire valid; priority_encoder4 dut(in,out,valid); initial begin in=4'b0001;#5 in=4'b0100;#5 $finish; end endmodule"
    },
    # 9. Comparator
    {
        "id": "TC09_CMP",
        "name": "8-Bit Magnitude Comparator",
        "category": "Basic Combinational",
        "is_failure_case": False,
        "rtl": """module comparator8 (
    input [7:0] a,
    input [7:0] b,
    output wire gt,
    output wire lt,
    output wire eq
);
    assign gt = (a > b);
    assign lt = (a < b);
    assign eq = (a == b);
endmodule""",
        "tb": "module tb; reg [7:0] a,b; wire gt,lt,eq; comparator8 dut(a,b,gt,lt,eq); initial begin a=10;b=20;#5 a=20;#5 a=30;#5 $finish; end endmodule"
    },
    # 10. D Flip-Flop
    {
        "id": "TC10_DFF",
        "name": "D Flip-Flop with Async Reset",
        "category": "Sequential",
        "is_failure_case": False,
        "rtl": """module dff_async (
    input clk,
    input rst_n,
    input d,
    output reg q
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            q <= 1'b0;
        else
            q <= d;
    end
endmodule""",
        "tb": "module tb; reg clk,rst_n,d; wire q; dff_async dut(clk,rst_n,d,q); always #5 clk=~clk; initial begin clk=0;rst_n=0;d=0;#15 rst_n=1;#10 d=1;#10 d=0;#20 $finish; end endmodule"
    },
    # 11. Register
    {
        "id": "TC11_REG",
        "name": "8-Bit Parallel Register",
        "category": "Sequential",
        "is_failure_case": False,
        "rtl": """module reg8 (
    input clk,
    input rst_n,
    input [7:0] d,
    output reg [7:0] q
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            q <= 8'h00;
        else
            q <= d;
    end
endmodule""",
        "tb": "module tb; reg clk,rst_n; reg [7:0] d; wire [7:0] q; reg8 dut(clk,rst_n,d,q); always #5 clk=~clk; initial begin clk=0;rst_n=0;d=8'hAA;#15 rst_n=1;#20 d=8'h55;#20 $finish; end endmodule"
    },
    # 12. Counter
    {
        "id": "TC12_CTR",
        "name": "8-Bit Up Counter",
        "category": "Sequential",
        "is_failure_case": False,
        "rtl": """module counter8 (
    input clk,
    input rst_n,
    input enable,
    output reg [7:0] count
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            count <= 8'h00;
        else if (enable)
            count <= count + 1'b1;
    end
endmodule""",
        "tb": "module tb; reg clk,rst_n,enable; wire [7:0] count; counter8 dut(clk,rst_n,enable,count); always #5 clk=~clk; initial begin clk=0;rst_n=0;enable=1;#15 rst_n=1;#50 $finish; end endmodule"
    },
    # 13. Up/Down Counter
    {
        "id": "TC13_UDCTR",
        "name": "Up/Down Counter",
        "category": "Sequential",
        "is_failure_case": False,
        "rtl": """module up_down_counter (
    input clk,
    input rst_n,
    input up,
    output reg [7:0] count
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            count <= 8'h00;
        else if (up)
            count <= count + 1'b1;
        else
            count <= count - 1'b1;
    end
endmodule""",
        "tb": "module tb; reg clk,rst_n,up; wire [7:0] count; up_down_counter dut(clk,rst_n,up,count); always #5 clk=~clk; initial begin clk=0;rst_n=0;up=1;#15 rst_n=1;#30 up=0;#30 $finish; end endmodule"
    },
    # 14. Shift Register
    {
        "id": "TC14_SHIFT",
        "name": "8-Bit Serial-In Parallel-Out Shift Register",
        "category": "Sequential",
        "is_failure_case": False,
        "rtl": """module shift_reg8 (
    input clk,
    input rst_n,
    input sin,
    output reg [7:0] pout
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            pout <= 8'h00;
        else
            pout <= {pout[6:0], sin};
    end
endmodule""",
        "tb": "module tb; reg clk,rst_n,sin; wire [7:0] pout; shift_reg8 dut(clk,rst_n,sin,pout); always #5 clk=~clk; initial begin clk=0;rst_n=0;sin=1;#15 rst_n=1;#10 sin=0;#10 sin=1;#40 $finish; end endmodule"
    },
    # 15. Clock Enable Register
    {
        "id": "TC15_CLKEN",
        "name": "Register with Clock Enable",
        "category": "Sequential",
        "is_failure_case": False,
        "rtl": """module reg_clken (
    input clk,
    input rst_n,
    input en,
    input [7:0] din,
    output reg [7:0] dout
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            dout <= 8'h00;
        else if (en)
            dout <= din;
    end
endmodule""",
        "tb": "module tb; reg clk,rst_n,en; reg [7:0] din; wire [7:0] dout; reg_clken dut(clk,rst_n,en,din,dout); always #5 clk=~clk; initial begin clk=0;rst_n=0;en=0;din=8'hFF;#15 rst_n=1;#10 en=1;#20 $finish; end endmodule"
    },
    # 16. Adder
    {
        "id": "TC16_ADD",
        "name": "8-Bit Binary Adder with Carry",
        "category": "Arithmetic",
        "is_failure_case": False,
        "rtl": """module adder8 (
    input [7:0] a,
    input [7:0] b,
    input cin,
    output wire [7:0] sum,
    output wire cout
);
    assign {cout, sum} = a + b + cin;
endmodule""",
        "tb": "module tb; reg [7:0] a,b; reg cin; wire [7:0] sum; wire cout; adder8 dut(a,b,cin,sum,cout); initial begin a=10;b=20;cin=0;#5 a=255;b=1;#5 $finish; end endmodule"
    },
    # 17. Subtractor
    {
        "id": "TC17_SUB",
        "name": "8-Bit Binary Subtractor",
        "category": "Arithmetic",
        "is_failure_case": False,
        "rtl": """module sub8 (
    input [7:0] a,
    input [7:0] b,
    output wire [7:0] diff,
    output wire borrow
);
    assign {borrow, diff} = a - b;
endmodule""",
        "tb": "module tb; reg [7:0] a,b; wire [7:0] diff; wire borrow; sub8 dut(a,b,diff,borrow); initial begin a=50;b=20;#5 a=10;b=20;#5 $finish; end endmodule"
    },
    # 18. Multiplier
    {
        "id": "TC18_MUL",
        "name": "4x4 Combinational Multiplier",
        "category": "Arithmetic",
        "is_failure_case": False,
        "rtl": """module mul4 (
    input [3:0] a,
    input [3:0] b,
    output wire [7:0] prod
);
    assign prod = a * b;
endmodule""",
        "tb": "module tb; reg [3:0] a,b; wire [7:0] prod; mul4 dut(a,b,prod); initial begin a=3;b=5;#5 a=15;b=15;#5 $finish; end endmodule"
    },
    # 19. Accumulator
    {
        "id": "TC19_ACC",
        "name": "16-Bit Synchronous Accumulator",
        "category": "Arithmetic",
        "is_failure_case": False,
        "rtl": """module accum16 (
    input clk,
    input rst_n,
    input clear,
    input [7:0] data_in,
    output reg [15:0] acc
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            acc <= 16'd0;
        else if (clear)
            acc <= 16'd0;
        else
            acc <= acc + data_in;
    end
endmodule""",
        "tb": "module tb; reg clk,rst_n,clear; reg [7:0] data_in; wire [15:0] acc; accum16 dut(clk,rst_n,clear,data_in,acc); always #5 clk=~clk; initial begin clk=0;rst_n=0;clear=0;data_in=10;#15 rst_n=1;#30 data_in=5;#20 $finish; end endmodule"
    },
    # 20. ALU
    {
        "id": "TC20_ALU",
        "name": "Arithmetic Logic Unit",
        "category": "Arithmetic",
        "is_failure_case": False,
        "rtl": """module alu_simple (
    input [1:0] op,
    input [7:0] a,
    input [7:0] b,
    output reg [7:0] out
);
    always @(*) begin
        case (op)
            2'b00: out = a + b;
            2'b01: out = a - b;
            2'b10: out = a & b;
            default: out = a ^ b;
        endcase
    end
endmodule""",
        "tb": "module tb; reg [1:0] op; reg [7:0] a,b; wire [7:0] out; alu_simple dut(op,a,b,out); initial begin a=20;b=5;op=0;#5 op=1;#5 op=2;#5 $finish; end endmodule"
    },
    # 21. FSM
    {
        "id": "TC21_FSM",
        "name": "3-State Sequence Detector",
        "category": "Control",
        "is_failure_case": False,
        "rtl": """module seq_fsm (
    input clk,
    input rst_n,
    input in_bit,
    output reg detected
);
    localparam S0 = 2'b00, S1 = 2'b01, S2 = 2'b10;
    reg [1:0] state, next_state;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) state <= S0;
        else state <= next_state;
    end

    always @(*) begin
        case (state)
            S0: next_state = in_bit ? S1 : S0;
            S1: next_state = in_bit ? S1 : S2;
            S2: next_state = in_bit ? S1 : S0;
            default: next_state = S0;
        endcase
    end

    always @(*) begin
        detected = (state == S2 && in_bit);
    end
endmodule""",
        "tb": "module tb; reg clk,rst_n,in_bit; wire detected; seq_fsm dut(clk,rst_n,in_bit,detected); always #5 clk=~clk; initial begin clk=0;rst_n=0;in_bit=1;#15 rst_n=1;#10 in_bit=0;#10 in_bit=1;#30 $finish; end endmodule"
    },
    # 22. Traffic Light
    {
        "id": "TC22_TRAFFIC",
        "name": "Intersection Traffic Light",
        "category": "Control",
        "is_failure_case": False,
        "rtl": """module traffic_controller (
    input clk,
    input rst_n,
    input sensor,
    output reg [1:0] light
);
    localparam RED = 2'b00, GREEN = 2'b01, YELLOW = 2'b10;
    reg [1:0] state;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) state <= RED;
        else case (state)
            RED: if (sensor) state <= GREEN;
            GREEN: state <= YELLOW;
            YELLOW: state <= RED;
            default: state <= RED;
        endcase
    end

    always @(*) light = state;
endmodule""",
        "tb": "module tb; reg clk,rst_n,sensor; wire [1:0] light; traffic_controller dut(clk,rst_n,sensor,light); always #5 clk=~clk; initial begin clk=0;rst_n=0;sensor=1;#15 rst_n=1;#40 $finish; end endmodule"
    },
    # 23. UART TX
    {
        "id": "TC23_UARTTX",
        "name": "UART Transmitter Core",
        "category": "Control",
        "is_failure_case": False,
        "rtl": """module uart_tx_core (
    input clk,
    input rst_n,
    input start,
    input [7:0] din,
    output reg tx,
    output reg done
);
    reg [3:0] bit_cnt;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            tx <= 1'b1;
            done <= 1'b1;
            bit_cnt <= 4'd0;
        end else if (start) begin
            tx <= 1'b0;
            done <= 1'b0;
            bit_cnt <= 4'd8;
        end else if (bit_cnt > 0) begin
            tx <= din[8 - bit_cnt];
            bit_cnt <= bit_cnt - 1'b1;
        end else begin
            tx <= 1'b1;
            done <= 1'b1;
        end
    end
endmodule""",
        "tb": "module tb; reg clk,rst_n,start; reg [7:0] din; wire tx,done; uart_tx_core dut(clk,rst_n,start,din,tx,done); always #5 clk=~clk; initial begin clk=0;rst_n=0;start=0;din=8'h55;#15 rst_n=1;#10 start=1;#10 start=0;#90 $finish; end endmodule"
    },
    # 24. UART RX
    {
        "id": "TC24_UARTRX",
        "name": "UART Receiver Core",
        "category": "Control",
        "is_failure_case": False,
        "rtl": """module uart_rx_core (
    input clk,
    input rst_n,
    input rx,
    output reg [7:0] dout,
    output reg valid
);
    reg [2:0] state;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            dout <= 8'h00;
            valid <= 1'b0;
            state <= 3'd0;
        end else begin
            if (state == 0 && !rx) begin
                state <= 1;
                valid <= 1'b0;
            end else if (state > 0 && state <= 8) begin
                dout[state-1] <= rx;
                state <= state + 1'b1;
            end else if (state == 9) begin
                valid <= 1'b1;
                state <= 0;
            end
        end
    end
endmodule""",
        "tb": "module tb; reg clk,rst_n,rx; wire [7:0] dout; wire valid; uart_rx_core dut(clk,rst_n,rx,dout,valid); always #5 clk=~clk; initial begin clk=0;rst_n=0;rx=1;#15 rst_n=1;#10 rx=0;#10 rx=1;#90 $finish; end endmodule"
    },
    # 25. SPI Controller
    {
        "id": "TC25_SPI",
        "name": "SPI Master Interface",
        "category": "Control",
        "is_failure_case": False,
        "rtl": """module spi_master (
    input clk,
    input rst_n,
    input start,
    input [7:0] tx_data,
    output reg sclk,
    output reg mosi,
    output reg cs_n
);
    reg [2:0] count;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            sclk <= 1'b0;
            mosi <= 1'b0;
            cs_n <= 1'b1;
            count <= 3'd0;
        end else if (start) begin
            cs_n <= 1'b0;
            count <= 3'd7;
            mosi <= tx_data[7];
        end else if (!cs_n) begin
            sclk <= ~sclk;
            if (sclk) begin
                if (count == 0) cs_n <= 1'b1;
                else begin
                    count <= count - 1'b1;
                    mosi <= tx_data[count - 1];
                end
            end
        end
    end
endmodule""",
        "tb": "module tb; reg clk,rst_n,start; reg [7:0] tx_data; wire sclk,mosi,cs_n; spi_master dut(clk,rst_n,start,tx_data,sclk,mosi,cs_n); always #5 clk=~clk; initial begin clk=0;rst_n=0;start=0;tx_data=8'hC3;#15 rst_n=1;#10 start=1;#10 start=0;#100 $finish; end endmodule"
    },
    # 26. Register File
    {
        "id": "TC26_REGFILE",
        "name": "4x8 Multi-Port Register File",
        "category": "Memory",
        "is_failure_case": False,
        "rtl": """module regfile4x8 (
    input clk,
    input we,
    input [1:0] waddr,
    input [7:0] wdata,
    input [1:0] raddr1,
    output wire [7:0] rdata1
);
    reg [7:0] rf [0:3];
    always @(posedge clk) begin
        if (we)
            rf[waddr] <= wdata;
    end
    assign rdata1 = rf[raddr1];
endmodule""",
        "tb": "module tb; reg clk,we; reg [1:0] waddr,raddr1; reg [7:0] wdata; wire [7:0] rdata1; regfile4x8 dut(clk,we,waddr,wdata,raddr1,rdata1); always #5 clk=~clk; initial begin clk=0;we=1;waddr=0;wdata=8'h42;raddr1=0;#10 waddr=1;wdata=8'h99;#10 we=0;raddr1=1;#20 $finish; end endmodule"
    },
    # 27. Synchronous RAM
    {
        "id": "TC27_RAM",
        "name": "Synchronous RAM 16x8",
        "category": "Memory",
        "is_failure_case": False,
        "rtl": """module sync_ram (
    input clk,
    input cs,
    input we,
    input [3:0] addr,
    input [7:0] din,
    output reg [7:0] dout
);
    reg [7:0] memory [0:15];
    always @(posedge clk) begin
        if (cs) begin
            if (we)
                memory[addr] <= din;
            dout <= memory[addr];
        end
    end
endmodule""",
        "tb": "module tb; reg clk,cs,we; reg [3:0] addr; reg [7:0] din; wire [7:0] dout; sync_ram dut(clk,cs,we,addr,din,dout); always #5 clk=~clk; initial begin clk=0;cs=1;we=1;addr=4;din=8'h5A;#10 we=0;#10 $finish; end endmodule"
    },
    # 28. FIFO
    {
        "id": "TC28_FIFO",
        "name": "Synchronous FIFO Buffer",
        "category": "Memory",
        "is_failure_case": False,
        "rtl": """module fifo_small (
    input clk,
    input rst_n,
    input push,
    input pop,
    input [7:0] din,
    output reg [7:0] dout,
    output wire empty
);
    reg [7:0] buffer [0:3];
    reg [1:0] count;
    assign empty = (count == 0);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) count <= 0;
        else if (push && !pop && count < 3) count <= count + 1'b1;
        else if (pop && !push && count > 0) count <= count - 1'b1;
    end
endmodule""",
        "tb": "module tb; reg clk,rst_n,push,pop; reg [7:0] din; wire [7:0] dout; wire empty; fifo_small dut(clk,rst_n,push,pop,din,dout,empty); always #5 clk=~clk; initial begin clk=0;rst_n=0;push=0;pop=0;#15 rst_n=1;#10 push=1;din=12;#20 pop=1;#20 $finish; end endmodule"
    },
    # 29. Datapath
    {
        "id": "TC29_DATAPATH",
        "name": "Simple 3-Stage Datapath",
        "category": "Processor",
        "is_failure_case": False,
        "rtl": """module datapath3 (
    input clk,
    input rst_n,
    input [7:0] in_a,
    input [7:0] in_b,
    input add_sub_n,
    output reg [7:0] out_q
);
    reg [7:0] stage1_a, stage1_b;
    reg [7:0] stage2_res;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            stage1_a <= 8'd0;
            stage1_b <= 8'd0;
            stage2_res <= 8'd0;
            out_q <= 8'd0;
        end else begin
            stage1_a <= in_a;
            stage1_b <= in_b;
            stage2_res <= add_sub_n ? (stage1_a + stage1_b) : (stage1_a - stage1_b);
            out_q <= stage2_res;
        end
    end
endmodule""",
        "tb": "module tb; reg clk,rst_n,add_sub_n; reg [7:0] in_a,in_b; wire [7:0] out_q; datapath3 dut(clk,rst_n,in_a,in_b,add_sub_n,out_q); always #5 clk=~clk; initial begin clk=0;rst_n=0;add_sub_n=1;in_a=10;in_b=5;#15 rst_n=1;#40 $finish; end endmodule"
    },
    # 30. RISC-V Datapath
    {
        "id": "TC30_RISCV",
        "name": "RISC-V Execute Stage ALU",
        "category": "Processor",
        "is_failure_case": False,
        "rtl": """module riscv_exec (
    input clk,
    input rst_n,
    input [31:0] rs1,
    input [31:0] rs2,
    input [2:0] funct3,
    output reg [31:0] rd
);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) rd <= 32'd0;
        else case (funct3)
            3'b000: rd <= rs1 + rs2; // ADD
            3'b111: rd <= rs1 & rs2; // AND
            3'b110: rd <= rs1 | rs2; // OR
            default: rd <= rs1 ^ rs2;// XOR
        endcase
    end
endmodule""",
        "tb": "module tb; reg clk,rst_n; reg [31:0] rs1,rs2; reg [2:0] funct3; wire [31:0] rd; riscv_exec dut(clk,rst_n,rs1,rs2,funct3,rd); always #5 clk=~clk; initial begin clk=0;rst_n=0;rs1=100;rs2=50;funct3=0;#15 rst_n=1;#30 $finish; end endmodule"
    },
    # 31. Width mismatch
    {
        "id": "TC31_WIDTH_MISMATCH",
        "name": "Bit Width Mismatch Failure",
        "category": "RTL Quality Failure",
        "is_failure_case": True,
        "expected_issue": "Width Mismatch",
        "rtl": """module fail_width (
    input [7:0] a,
    output wire [3:0] b
);
    assign b = 8'hFF; // 8-bit literal into 4-bit wire
endmodule""",
        "tb": "module tb; reg [7:0] a; wire [3:0] b; fail_width dut(a,b); initial begin a=0;#10 $finish; end endmodule"
    },
    # 32. Multiple driver
    {
        "id": "TC32_MULTI_DRIVER",
        "name": "Multiple Drivers Failure",
        "category": "RTL Quality Failure",
        "is_failure_case": True,
        "expected_issue": "Multiple Drivers",
        "rtl": """module fail_multidrv (
    input clk,
    input a,
    input b,
    output wire y
);
    assign y = a;
    assign y = b; // Multiple driver!
endmodule""",
        "tb": "module tb; reg clk,a,b; wire y; fail_multidrv dut(clk,a,b,y); initial begin a=0;b=1;#10 $finish; end endmodule"
    },
    # 33. Latch inference
    {
        "id": "TC33_LATCH",
        "name": "Inferred Latch Failure",
        "category": "RTL Quality Failure",
        "is_failure_case": True,
        "expected_issue": "Latch Inference",
        "rtl": """module fail_latch (
    input en,
    input [7:0] d,
    output reg [7:0] q
);
    always @(*) begin
        if (en)
            q = d; // missing else branch causes latch inference!
    end
endmodule""",
        "tb": "module tb; reg en; reg [7:0] d; wire [7:0] q; fail_latch dut(en,d,q); initial begin en=1;d=5;#10 en=0;#10 $finish; end endmodule"
    },
    # 34. Missing reset
    {
        "id": "TC34_NO_RESET",
        "name": "Sequential Logic Missing Reset",
        "category": "RTL Quality Failure",
        "is_failure_case": True,
        "expected_issue": "Missing Reset",
        "rtl": """module fail_no_reset (
    input clk,
    input [7:0] d,
    output reg [7:0] q
);
    always @(posedge clk) begin
        q <= d; // No reset condition in sequential block!
    end
endmodule""",
        "tb": "module tb; reg clk; reg [7:0] d; wire [7:0] q; fail_no_reset dut(clk,d,q); always #5 clk=~clk; initial begin clk=0;d=8'h12;#20 $finish; end endmodule"
    },
    # 35. Incomplete case statement
    {
        "id": "TC35_INCOMPLETE_CASE",
        "name": "Incomplete Case Statement Failure",
        "category": "RTL Quality Failure",
        "is_failure_case": True,
        "expected_issue": "Latch Inference",
        "rtl": """module fail_case (
    input [1:0] sel,
    output reg [3:0] y
);
    always @(*) begin
        case (sel)
            2'b00: y = 4'b0001;
            2'b01: y = 4'b0010;
            // missing 2'b10, 2'b11, and missing default!
        endcase
    end
endmodule""",
        "tb": "module tb; reg [1:0] sel; wire [3:0] y; fail_case dut(sel,y); initial begin sel=0;#10 $finish; end endmodule"
    },
    # 36. Combinational loop
    {
        "id": "TC36_COMB_LOOP",
        "name": "Combinational Feedback Loop Failure",
        "category": "RTL Quality Failure",
        "is_failure_case": True,
        "expected_issue": "Combinational Loop",
        "rtl": """module fail_comb_loop (
    input a,
    output wire y
);
    wire loop_a, loop_b;
    assign loop_a = loop_b ^ a;
    assign loop_b = ~loop_a; // Combinational race condition loop!
    assign y = loop_a;
endmodule""",
        "tb": "module tb; reg a; wire y; fail_comb_loop dut(a,y); initial begin a=1;#10 $finish; end endmodule"
    },
    # 37. Unused signal
    {
        "id": "TC37_UNUSED_SIGNAL",
        "name": "Unused Signal Warning",
        "category": "RTL Quality Failure",
        "is_failure_case": True,
        "expected_issue": "Unused Signal",
        "rtl": """module fail_unused (
    input a,
    output wire y
);
    wire unused_wire; // Declared but never used!
    assign y = ~a;
endmodule""",
        "tb": "module tb; reg a; wire y; fail_unused dut(a,y); initial begin a=0;#10 $finish; end endmodule"
    },
    # 38. Unreachable FSM state
    {
        "id": "TC38_UNREACHABLE_FSM",
        "name": "Incomplete Sensitivity or Unreachable State",
        "category": "RTL Quality Failure",
        "is_failure_case": True,
        "expected_issue": "Sensitivity List",
        "rtl": """module fail_sensitivity (
    input a,
    input b,
    output reg y
);
    always @(a) begin // b is read inside body but omitted from sensitivity!
        y = a & b;
    end
endmodule""",
        "tb": "module tb; reg a,b; wire y; fail_sensitivity dut(a,b,y); initial begin a=1;b=0;#10 $finish; end endmodule"
    },
    # 39. Undriven output
    {
        "id": "TC39_UNDRIVEN_OUT",
        "name": "Undriven Output Port Failure",
        "category": "RTL Quality Failure",
        "is_failure_case": True,
        "expected_issue": "Undriven Output",
        "rtl": """module fail_undriven (
    input a,
    output wire y,
    output wire floating_out // Declared but never driven!
);
    assign y = a;
endmodule""",
        "tb": "module tb; reg a; wire y,floating_out; fail_undriven dut(a,y,floating_out); initial begin a=1;#10 $finish; end endmodule"
    },
    # 40. Testbench with no checking
    {
        "id": "TC40_BAD_TB",
        "name": "Testbench with No Checking Failure",
        "category": "RTL Quality Failure",
        "is_failure_case": True,
        "expected_issue": "Output Verification",
        "rtl": """module simple_buf (
    input a,
    output wire y
);
    assign y = a;
endmodule""",
        "tb": """module tb_bad;
    reg a;
    wire y;
    simple_buf dut(a,y);
    initial begin
        a = 1; #10; a = 0; #10; // Drives input but never inspects or checks 'y'
        $finish;
    end
endmodule"""
    }
]
