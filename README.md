# Partial simulation of Xilinx xc7k160t JTAG TAP

For amusement...

```sh
$ python3 -m xvc_sim
```

Server listening on localhost at TCP port 2541.
Connect with Xilinx tools.  eg. `xsct`

```
$ xsct -nodisp
xsct% connect -xvc-url TCP:127.0.0.1:2542
attempting to launch hw_server
...
xsct% targets
  1  xc7k160t
xsct% jtag targets
  1  Xilinx Virtual Cable 127.0.0.1:2542
     2  xc7k160t (idcode 0364c093 irlen 6 fpga)
xsct% fpga -state
FPGA is not configured
xsct% fpga -ir-status
IR STATUS: 17
     Always One (Bits [0]): 1
    Always Zero (Bits [1]): 0
       ISC_Done (Bits [2]): 0
    ISC_Enabled (Bits [3]): 0
  Init Complete (Bits [4]): 1
           DONE (Bits [5]): 0
```
