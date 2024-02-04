"""Copyright 2024 Michael Davidsaver
License: GPL-3
"""

import asyncio
import signal
import logging
import struct
from enum import Enum, IntEnum

_log = logging.getLogger(__name__)

_u32 = struct.Struct('<I')

def unbin(s: str, *, flip=False):
    ret = []
    for c in s:
        if c=='0':
            ret.append(False)
        elif c=='1':
            ret.append(True)
        elif c==' ':
            pass
        else:
            assert ValueError(c)
    if flip:
        ret.reverse()
    return ret

def unhex(n: int, b: bytes):
    R = []
    for i in range(n):
        by, bi = divmod(i, 8)
        R.append((b[by] & (1<<bi))!=0)
    return R

# simulated IR length 6 bits
class Instr(Enum):
    # cf. xc7k160t
    # 7 series, UG470 v1.17
    EXTEST     =unbin('10 0110')
    SAMPLE     =unbin('00 0001')
    USER1      =unbin('00 0010')
    USER2      =unbin('00 0011')
    USER3      =unbin('10 0010')
    USER4      =unbin('10 0011')
    CFG_IN     =unbin('00 0101')
    CFG_OUT    =unbin('00 0100')
    IDCODE     =unbin('00 1001')
    JPROGRAM   =unbin('00 1011')
    JSTART     =unbin('00 1100')
    JSHUTDOWN  =unbin('00 1101')
    ISC_ENABLE =unbin('01 0000')
    ISC_PROGRAM=unbin('01 0001')
    ISC_NOOP   =unbin('01 0100')
    ISC_DISABLE=unbin('01 0110')
    BYPASS     =unbin('11 1111')

# JTAG states
class State(Enum):
    Reset = 0
    Idle = 1
    SelDR = 2
    SelIR = 3
    CapDR = 4
    CapIR = 5
    ShiftDR = 6
    ShiftIR = 7
    Exit1DR = 8
    Exit1IR = 9
    PauseDR = 10
    PauseIR = 11
    Exit2DR = 12
    Exit2IR = 13
    UpdateDR = 14
    UpdateIR = 15

# JTAG state machine transitions
_next_state = {
    # current  : (TMS==0, TMS==1),
    State.Reset: (State.Idle, State.Reset),
    State.Idle:  (State.Idle, State.SelDR),
    State.SelDR: (State.CapDR, State.SelIR),
    State.SelIR: (State.CapIR, State.Reset),
    State.CapDR: (State.ShiftDR, State.Exit1DR),
    State.CapIR: (State.ShiftIR, State.Exit1IR),
    State.ShiftDR: (State.ShiftDR, State.Exit1DR),
    State.ShiftIR: (State.ShiftIR, State.Exit1IR),
    State.Exit1DR: (State.PauseDR, State.UpdateDR),
    State.Exit1IR: (State.PauseIR, State.UpdateIR),
    State.PauseDR: (State.PauseDR, State.Exit2DR),
    State.PauseIR: (State.PauseIR, State.Exit2IR),
    State.Exit2DR: (State.ShiftDR, State.UpdateDR),
    State.Exit2IR: (State.ShiftIR, State.UpdateIR),
    State.UpdateDR: (State.Idle, State.SelDR),
    State.UpdateIR: (State.Idle, State.SelDR),
}
assert len(_next_state)==16, len(_next_state)

#class Device:
#    def __init__(self, idcode=0, bsr=[False]):
#        self.bsr = list(bsr)
#        self.bypass = [False]

class Chain:
    _state: State
    def __init__(self):
        self._state = State.Reset
        self._inst = Instr.IDCODE # really default?
        self._DRs = {
            Instr.BYPASS: [True],
            Instr.IDCODE: unbin('0000 0011 0110 0100 1100 0000 1001 0011'), # 0x0364c093 xc7k160t
            # TODO: actual length?
            Instr.CFG_IN: [False]*16,
            Instr.CFG_OUT: [False]*16,
            # hw_server likes to interrogate these
            Instr.USER1: [True],
            Instr.USER2: [True],
            Instr.USER3: [True],
            Instr.USER4: [True],
        }
        self._IR = self._DR = None
        assert len(self._DRs[Instr.IDCODE])==32

    def shift(self, tms: bool, tdi: bool) -> bool:
        tdo = True # simulate pull-up when undriven
        # states with side-effects
        if self._state==State.Reset:
            self._inst = Instr.IDCODE
            _log.debug('RESET %s', self._inst)

        elif self._state==State.CapIR:
            # JTAG standard says 0b..10, xlinx 7 series has 0b..01, openFPGALoader insists on 0b...1
            # [DONE, INIT, ISC_ENABLE, ISC_DONE, False, True]
            self._IR = [False, True, False, False, False, True]
            _log.debug('INIT IR %r', self._IR)

        elif self._state==State.CapDR:
            self._DR = list(self._DRs[self._inst])
            _log.info('LOAD DR %s %r', self._inst, self._DR)

        elif self._state==State.ShiftIR:
            # shift in from "high" end (list index 0)
            tdo = self._IR[-1]
            self._IR = [tdi] + self._IR[0:-1]

        elif self._state==State.ShiftDR:
            tdo = self._DR[-1]
            self._DR = [tdi] + self._DR[0:-1]

        elif self._state==State.UpdateIR:
            try:
                self._inst = Instr(self._IR)
                _log.info('INSTR %s', self._inst)
            except ValueError:
                self._inst = Instr.BYPASS
                _log.warning('INSTR UNKNOWN -> BYPASS : %r', self._IR)

        elif self._state==State.UpdateDR:
            _log.info('EXEC %s %r', self._inst, self._DR)
            #self._DRs[self._inst] = list(self._DR) # TODO: save values?

        next_state = _next_state[self._state][1 if tms else 0]
        #_log.debug('Shift TMS=%s TDI=%s TDO=%s %s -> %s', tms, tdi, tdo, self._state, next_state)
        self._state = next_state
        return tdo

    async def client(self, R: asyncio.StreamReader, W: asyncio.StreamWriter):
        try:
            _log.info('Client connect')
            while True:
                cmd = await R.readuntil(b':')
                _log.debug('CMD %r', cmd)

                if cmd==b'getinfo:':
                    W.write(b'xvcServer_v1.0:1024\n')

                elif cmd==b'settck:':
                    period, = _u32.unpack(await R.readexactly(4))
                    _log.info('settck %d ns', period)
                    W.write(_u32.pack(period))

                elif cmd==b'shift:':
                    nbits, = _u32.unpack(await R.readexactly(4))
                    _log.debug('shift %d bits', nbits)

                    nbytes = (nbits + 7)//8
                    TMSs = await R.readexactly(nbytes)
                    TDIs = await R.readexactly(nbytes)
                    TDOs = bytearray(nbytes)
                    _log.debug('TMS %r', TMSs)
                    _log.debug('TDI %r', TDIs)
                    _log.debug('BEGIN %s', self._state)

                    for idx in range(nbits):
                        byte, bit = divmod(idx, 8)
                        tms = TMSs[byte]&(1<<bit) != 0
                        tdi = TDIs[byte]&(1<<bit) != 0
                        tdo = self.shift(tms, tdi)
                        if tdo:
                            TDOs[byte] |= 1<<bit

                    _log.debug('FINAL %s', self._state)
                    _log.debug('TDO %r', TDOs)
                    W.write(TDOs)

                else:
                    raise RuntimeError(f'Unknown command {cmd!r}')

                await W.drain()
        except asyncio.IncompleteReadError as e:
            if e.partial:
                _log.debug('incomplete %s %r', e.expected, e.partial)

        finally:
            W.close()
            await W.wait_closed()
            _log.info('Client disconnect')

def getargs():
    from argparse import ArgumentParser
    P = ArgumentParser()
    P.add_argument('-v', '--verbose', action='store_const', const=logging.DEBUG,
                   dest='level', default=logging.INFO,
                   help='Make more noise')
    P.add_argument('-q', '--quiet', action='store_const', const=logging.WARN,
                   dest='level',
                   help='Make less noise')
    return P

async def main():
    args = getargs().parse_args()
    logging.basicConfig(level=args.level)
    chain = Chain()

    loop = asyncio.get_running_loop()
    srv = await asyncio.start_server(chain.client, host='localhost', port=2542)

    done = asyncio.Event()
    loop.add_signal_handler(signal.SIGINT, done.set)
    _log.info('Running')
    try:
        await done.wait()
    except asyncio.CancelledError:
        pass
    _log.info('Stop')

    srv.close()
    await srv.wait_closed()
    _log.info('Done')
