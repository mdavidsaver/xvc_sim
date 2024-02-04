"""Copyright 2024 Michael Davidsaver
License: GPL-3
"""

import pytest
from .. import unbin, unhex, Chain, State, Instr

def test_unhex():
    tms = unhex(43, b'_\x00\x00\x00\x00\x03')
    assert tms==[True, True, True, True, True, False, True, False] + [False]*32 + [True, True, False]

def test_unbin():
    B = unbin('1010')
    # index 0 is MSB
    assert B==[True, False, True, False]

class Shifter:
    def __init__(self):
        self.chain = Chain()

    def shift(self, tms: [bool], tdi: [bool] = None) -> [bool]:
        assert len(tms), tms
        tdi = tdi or [False]*len(tms)
        tdo = []
        for m, i in zip(tms, tdi):
            tdo.append(self.chain.shift(m, i))
        return tdo

    def assert_shift(self, *, tms, tdi=None, expect_tdo=None,
                     instr=None,
                     istate=None, fstate=None):
        if istate is not None:
            assert istate==self.chain._state, (istate, self.chain._state)
        tdo = self.shift(tms, tdi)
        if instr is not None:
            assert instr==self.chain._inst
        if fstate is not None:
            assert fstate==self.chain._state, (fstate, self.chain._state)
        if expect_tdo is not None:
            assert tdo==expect_tdo, (tdo, expect_tdo)

    def reset(self):
        self.assert_shift(tms=[True]*5, fstate=State.Reset)

def test_reset_idcode():
    """Reset and shift out IDCODE from data register
    """
    C = Shifter()
    C.reset()
    C.assert_shift(tms=[False], fstate=State.Idle)
    C.assert_shift(tms=[True], fstate=State.SelDR, instr=Instr.IDCODE)
    C.assert_shift(tms=[False], fstate=State.CapDR)
    C.assert_shift(tms=[False], fstate=State.ShiftDR)
    assert C.chain._DR==unbin('0000 0011 0110 0100 1100 0000 1001 0011')

    C.assert_shift(tms=[False]*32,
                   istate=State.ShiftDR,
                   fstate=State.ShiftDR,
                   expect_tdo=unbin('0000 0011 0110 0100 1100 0000 1001 0011', flip=True))
    assert C.chain._DR==[False]*32

    C.assert_shift(tms=[False]*32,
                   tdi=[True]+[False]*31,
                   istate=State.ShiftDR,
                   fstate=State.ShiftDR,
                   expect_tdo=[False]*32)
    assert C.chain._DR==[False]*31+[True]

    C.assert_shift(tms=[False]*32,
                   tdi=[False]+[True]*31,
                   istate=State.ShiftDR,
                   fstate=State.ShiftDR,
                   expect_tdo=[True]+[False]*31)
    assert C.chain._DR==[True]*31+[False]

    C.assert_shift(tms=[True, True, False], fstate=State.Idle)

def test_scan_bypass():
    """Detect number of devices in chain
    """
    C = Shifter()
    C.reset()
    C.assert_shift(tms=[False, True, True, False, False],
                   istate=State.Reset,
                   fstate=State.ShiftIR)
    assert C.chain._IR==unbin('01 0001')
    C.assert_shift(tms=[False]*32,
                   tdi=[True]*32,
                   istate=State.ShiftIR,
                   fstate=State.ShiftIR,
                   expect_tdo=unbin('1111 1111 1111 1111 1111 1111 1101 0001', flip=True))

    C.assert_shift(tms=[True, True, True, False, False], fstate=State.ShiftDR)
    assert C.chain._inst==Instr.BYPASS

    C.assert_shift(tms=[False]*32,
                   tdi=unbin('1111 1111 1111 1111 1111 1111 1101 0001', flip=True),
                   istate=State.ShiftDR,
                   fstate=State.ShiftDR,
                   expect_tdo=unbin('111 1111 1111 1111 1111 1111 1101 0001 1', flip=True))

    C.assert_shift(tms=[True, True, False], fstate=State.Idle)

def test_hw_reset():
    """Initial probe a la. hw_server
    """
    C = Shifter()
    #C.reset()
    # reset and shift out 32-bits for current (IDCODE) DR
    C.assert_shift(tms=unhex(43, b'_\x00\x00\x00\x00\x03'),
                   tdi=unhex(43, b'\x00\xfe\x01\x00\x00\x00'),
                   expect_tdo=unhex(43, b'\xff\'\x81\xc9\x06\x06'),
                   istate=State.Reset,
                   fstate=State.Idle)

    C.assert_shift(tms=unhex(78, b'\xff\x02\x00\x00\x00\x00\x00\x00\x00\x18'),
                   tdi=unhex(78, b'\x00\xf0\x0f\x00\x00\xf0\x0f\x00\x00\x00'),
                   expect_tdo=unhex(78,
                                 b'\xff?\tL6\xf0\x0f\x00\x000'),
                   istate=State.Idle,
                   fstate=State.Idle)
