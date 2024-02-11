

all: test

clean:
	rm -f *.vvp *.vcd

.PHONY: all test clean

test: test.vcd

test.vcd: test.vvp
	./$<

test.vvp: test.v tap_top.v tap_defines.v timescale.v
	iverilog -o $@ -DSIM -g2012 -Wall $^
