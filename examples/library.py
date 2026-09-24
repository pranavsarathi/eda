# Collection of pre-loaded educational Verilog designs with testbenches
# Exactly 4 canonical examples: Counter, ALU, FSM, Vending Machine

EXAMPLES = {
    "counter": {
        "id": "counter",
        "name": "Counter",
        "category": "Sequential",
        "description": "8-bit synchronous up-counter with load, enable, and terminal count flag.",
        "rtl": """module counter_8bit (
    input clk,
    input rst_n,
    input enable,
    input load,
    input [7:0] load_data,
    output reg [7:0] count,
    output wire terminal_count
);
    assign terminal_count = (count == 8'hFF);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            count <= 8'h00;
        else if (load)
            count <= load_data;
        else if (enable)
            count <= count + 1'b1;
    end
endmodule""",
        "tb": """module tb_counter_8bit;
    reg clk, rst_n, enable, load;
    reg [7:0] load_data;
    wire [7:0] count;
    wire terminal_count;

    counter_8bit dut (
        .clk(clk), .rst_n(rst_n), .enable(enable),
        .load(load), .load_data(load_data),
        .count(count), .terminal_count(terminal_count)
    );

    always #5 clk = ~clk;

    initial begin
        clk = 0; rst_n = 0; enable = 0; load = 0; load_data = 8'h00;
        #15 rst_n = 1;
        $display("[TB START] Counter reset released. Initial count=%0d", count);

        #10 enable = 1;
        #40 $display("[TB] Counting enabled... Current count=%0d", count);

        #10 load = 1; load_data = 8'hFD;
        #10 load = 0;
        $display("[TB] Loaded 8'hFD. Current count=%0d", count);

        #20 $display("[TB] Terminal count reached: terminal_count=%b count=%0d", terminal_count, count);
        #10 $finish;
    end
endmodule"""
    },

    "alu": {
        "id": "alu",
        "name": "ALU",
        "category": "Arithmetic",
        "description": "8-bit multi-operation arithmetic logic unit supporting ADD, SUB, AND, OR, XOR with Zero and Overflow flags.",
        "rtl": """module alu_8bit (
    input clk,
    input rst_n,
    input [2:0] opcode,
    input [7:0] a,
    input [7:0] b,
    output reg [7:0] result,
    output reg zero_flag,
    output reg overflow_flag
);
    wire [8:0] sum = a + b;
    wire [8:0] diff = a - b;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            result <= 8'h00;
            zero_flag <= 1'b1;
            overflow_flag <= 1'b0;
        end else begin
            case (opcode)
                3'b000: begin result <= sum[7:0]; overflow_flag <= sum[8]; end
                3'b001: begin result <= diff[7:0]; overflow_flag <= diff[8]; end
                3'b010: begin result <= a & b; overflow_flag <= 1'b0; end
                3'b011: begin result <= a | b; overflow_flag <= 1'b0; end
                3'b100: begin result <= a ^ b; overflow_flag <= 1'b0; end
                3'b101: begin result <= a << 1; overflow_flag <= a[7]; end
                3'b110: begin result <= a >> 1; overflow_flag <= a[0]; end
                default: begin result <= ~a; overflow_flag <= 1'b0; end
            endcase
            zero_flag <= (result == 8'h00);
        end
    end
endmodule""",
        "tb": """module tb_alu_8bit;
    reg clk, rst_n;
    reg [2:0] opcode;
    reg [7:0] a, b;
    wire [7:0] result;
    wire zero_flag, overflow_flag;

    alu_8bit dut (
        .clk(clk), .rst_n(rst_n), .opcode(opcode),
        .a(a), .b(b), .result(result),
        .zero_flag(zero_flag), .overflow_flag(overflow_flag)
    );

    always #5 clk = ~clk;

    initial begin
        clk = 0; rst_n = 0; opcode = 0; a = 8'd25; b = 8'd10;
        #15 rst_n = 1;

        #10 opcode = 3'b000; // ADD
        #10 $display("[TB] ADD: 25 + 10 = %0d (overflow=%b zero=%b)", result, overflow_flag, zero_flag);

        #10 opcode = 3'b001; // SUB
        #10 $display("[TB] SUB: 25 - 10 = %0d (overflow=%b zero=%b)", result, overflow_flag, zero_flag);

        #10 opcode = 3'b010; // AND
        #10 $display("[TB] AND: 25 & 10 = %0d", result);

        #10 opcode = 3'b100; // XOR
        #10 $display("[TB] XOR: 25 ^ 10 = %0d", result);

        #20 $finish;
    end
endmodule"""
    },

    "fsm": {
        "id": "fsm",
        "name": "FSM",
        "category": "Control",
        "description": "Moore state machine controlling Highway/Farmroad traffic lights with timer expiration inputs.",
        "rtl": """module fsm_traffic_light (
    input clk,
    input rst_n,
    input car_present,
    input timer_expired,
    output reg [1:0] hw_light, // 00: Red, 01: Yellow, 10: Green
    output reg [1:0] fr_light
);
    localparam S_HW_GREEN  = 2'b00;
    localparam S_HW_YELLOW = 2'b01;
    localparam S_FR_GREEN  = 2'b10;
    localparam S_FR_YELLOW = 2'b11;

    reg [1:0] current_state, next_state;

    // State register
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            current_state <= S_HW_GREEN;
        else
            current_state <= next_state;
    end

    // Next-state logic
    always @(*) begin
        case (current_state)
            S_HW_GREEN: begin
                if (car_present && timer_expired)
                    next_state = S_HW_YELLOW;
                else
                    next_state = S_HW_GREEN;
            end
            S_HW_YELLOW: begin
                if (timer_expired)
                    next_state = S_FR_GREEN;
                else
                    next_state = S_HW_YELLOW;
            end
            S_FR_GREEN: begin
                if (!car_present || timer_expired)
                    next_state = S_FR_YELLOW;
                else
                    next_state = S_FR_GREEN;
            end
            S_FR_YELLOW: begin
                if (timer_expired)
                    next_state = S_HW_GREEN;
                else
                    next_state = S_FR_YELLOW;
            end
            default: next_state = S_HW_GREEN;
        endcase
    end

    // Output decoding logic
    always @(*) begin
        case (current_state)
            S_HW_GREEN:  begin hw_light = 2'b10; fr_light = 2'b00; end
            S_HW_YELLOW: begin hw_light = 2'b01; fr_light = 2'b00; end
            S_FR_GREEN:  begin hw_light = 2'b00; fr_light = 2'b10; end
            S_FR_YELLOW: begin hw_light = 2'b00; fr_light = 2'b01; end
            default:     begin hw_light = 2'b00; fr_light = 2'b00; end
        endcase
    end
endmodule""",
        "tb": """module tb_fsm_traffic_light;
    reg clk, rst_n, car_present, timer_expired;
    wire [1:0] hw_light, fr_light;

    fsm_traffic_light dut (
        .clk(clk), .rst_n(rst_n), .car_present(car_present),
        .timer_expired(timer_expired), .hw_light(hw_light), .fr_light(fr_light)
    );

    always #5 clk = ~clk;

    initial begin
        clk = 0; rst_n = 0; car_present = 0; timer_expired = 0;
        #15 rst_n = 1;
        $display("[TB] FSM initialized. Highway: Green (%b), Farmroad: Red (%b)", hw_light, fr_light);

        #10 car_present = 1; timer_expired = 1;
        #10 $display("[TB] Car detected on farmroad. Highway transitioning to Yellow (%b)", hw_light);

        #10 timer_expired = 1;
        #10 $display("[TB] Farmroad Green (%b), Highway Red (%b)", fr_light, hw_light);

        #30 $finish;
    end
endmodule"""
    },

    "vending_machine": {
        "id": "vending_machine",
        "name": "Vending Machine",
        "category": "Sequential",
        "description": "Canonical 5-state Moore FSM beverage dispenser with synchronous reset and coin inputs.",
        "rtl": """module vending_machine (
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
endmodule""",
        "tb": """module tb_vending_machine;
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
    }
}
