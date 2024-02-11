// Copyright 2024 Michael Davidsaver
// License: GPL-3

`timescale 1us/1us
module test;

`define DIAG(MSG) $display("# @%0t - %s", $time, MSG)

`define ASSERT(X,MSG) if(X) $display("ok - %s", MSG); else $display("not ok - %s", MSG)

`define ASSERT_EQUAL(X, Y, MSG) if((X)===(Y)) $display("ok - %x == %x %s", X, Y, MSG); else $display("not ok - %x == %x %s", X, Y, MSG)

reg tck = 1'b1;
reg tms = 1'b1;
reg tdi = 1'bz;
wire tdo_d;
wire tdo_e;
wire tdo = tdo_e ? tdo_d : 1'bz;

reg [31:0] tdo32;
always @(posedge tck)
    tdo32 <= {tdo, tdo32[31:1]};

tap_top dut(
    .tms_pad_i(tms),
    .tck_pad_i(tck),
    .trst_pad_i(1'b0),
    .tdi_pad_i(tdi),
    .tdo_pad_o(tdo_d),
    .tdo_padoe_o(tdo_e),
    .debug_tdi_i(1'b0),
    .bs_chain_tdi_i(1'b0),
    .mbist_tdi_i(1'b0)
);

task cycle;
    input mode;
    begin
        cycle_d(mode, 1'bz, 1'bz);
    end
endtask

task cycle_d;
    input mode;
    input din;
    input expect_tdo;
    begin
        // TCK initially high
        #4
        // DUT does not strictly follow the standard (TDO only changes on negedge TCK)
        // instead TDO is updated one sim. tick after posedge TCK.
        // So we wait at >=2 ticks to compensate.
        tdi <= din;
        tms <= mode;
        // DUT changes tdo
        tck <= 1'b0; // falling edge -> setup
        #4
        tck <= 1'b1; // rising edge -> sample
        if (expect_tdo!==tdo)
            $display("not ok - @%0t tdo %x != %x", $simtime, tdo, expect_tdo);
    end
endtask

initial
begin
    $dumpfile("test.vcd");
    $dumpvars(0,test);

    #10
    tck <= 1;

    `DIAG("Reseting");
    cycle_d(1, 1'bz, 1'bx);
    cycle(1);
    cycle(1);
    cycle(1);
    cycle(1);

    #2
    `ASSERT(dut.test_logic_reset, "RESET");

    cycle(0);

    #2
    `ASSERT(~dut.test_logic_reset, "!RESET");
    `ASSERT(dut.run_test_idle, "IDLE");

    cycle(1);
    cycle(0);
    cycle(0);

    #2
    `ASSERT(dut.shift_dr, "SHIFT_DR");

    // 0x149511c3 -> 0b0001_0100_1001_0101_0001_0001_1100_0011
    `DIAG("Shifting out IDCODE");

    cycle_d(0, 1'b0, 1'b1);
    cycle_d(0, 1'b1, 1'b1);
    cycle_d(0, 1'b0, 1'b0);
    cycle_d(0, 1'b1, 1'b0);

    cycle_d(0, 1'b0, 1'b0);
    cycle_d(0, 1'b1, 1'b0);
    cycle_d(0, 1'b0, 1'b1);
    cycle_d(0, 1'b1, 1'b1);

    cycle_d(0, 1'b0, 1'b1);
    cycle_d(0, 1'b1, 1'b0);
    cycle_d(0, 1'b0, 1'b0);
    cycle_d(0, 1'b1, 1'b0);

    cycle_d(0, 1'b0, 1'b1);
    cycle_d(0, 1'b1, 1'b0);
    cycle_d(0, 1'b0, 1'b0);
    cycle_d(0, 1'b1, 1'b0);

    cycle_d(0, 1'b0, 1'b1);
    cycle_d(0, 1'b1, 1'b0);
    cycle_d(0, 1'b0, 1'b1);
    cycle_d(0, 1'b1, 1'b0);

    cycle_d(0, 1'b0, 1'b1);
    cycle_d(0, 1'b1, 1'b0);
    cycle_d(0, 1'b0, 1'b0);
    cycle_d(0, 1'b1, 1'b1);

    cycle_d(0, 1'b0, 1'b0);
    cycle_d(0, 1'b1, 1'b0);
    cycle_d(0, 1'b0, 1'b1);
    cycle_d(0, 1'b1, 1'b0);

    cycle_d(0, 1'b0, 1'b1);
    cycle_d(0, 1'b1, 1'b0);
    cycle_d(0, 1'b0, 1'b0);
    cycle_d(1, 1'b1, 1'b0);
    `DIAG("Shifted");

    cycle(1);
    `ASSERT_EQUAL(tdo32, 32'h149511c3, "IDCODE");
    cycle(0);
    #2
    `ASSERT(dut.run_test_idle, "IDLE");
    `DIAG("Idling");

    cycle(1);
    cycle(1);
    cycle(0);
    cycle(0);
    #2
    `ASSERT(dut.shift_ir, "SHIFT IR");

    `DIAG("Shifting in IR BYPASS");

    // DUT IR is 4 bits wide, shift in some extra as well
    cycle_d(0, 1'b1, 1'b1);
    cycle_d(0, 1'b1, 1'b0);
    cycle_d(0, 1'b1, 1'b1);
    cycle_d(0, 1'b1, 1'b0);

    cycle_d(0, 1'b1, 1'b1);
    cycle_d(0, 1'b1, 1'b1);
    cycle_d(0, 1'b1, 1'b1);
    cycle_d(1, 1'b1, 1'b1);

    cycle(1);
    cycle(1);
    cycle(0);
    cycle(0);
    #2
    `ASSERT(dut.shift_dr, "SHIFT DR");
    `DIAG("Shifting through BYPASS");

    cycle_d(0, 1'b1, 1'b1); // BYPASS initially 1
    cycle_d(0, 1'b0, 1'b1);
    cycle_d(0, 1'b1, 1'b0);
    cycle_d(0, 1'b0, 1'b1);

    cycle_d(0, 1'b1, 1'b0);
    cycle_d(0, 1'b1, 1'b1);
    cycle_d(0, 1'b0, 1'b1);
    cycle_d(0, 1'b0, 1'b0);

    cycle_d(0, 1'b1, 1'b0);
    cycle_d(0, 1'b1, 1'b1);
    cycle_d(0, 1'b1, 1'b1);
    cycle_d(0, 1'b0, 1'b1);
    cycle_d(0, 1'b0, 1'b0);
    cycle_d(0, 1'b0, 1'b0);
    cycle_d(1, 1'bz, 1'b0);

    cycle(1);
    cycle(0);
    #2
    `ASSERT(dut.run_test_idle, "IDLE");

    #10
    $finish();
end

endmodule
