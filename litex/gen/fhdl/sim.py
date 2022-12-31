#
# This file is part of LiteX (Adapted from Migen for LiteX usage).
#
# This file is Copyright (c) 2022 Jevin Sweval <jevin.sweval@gmail.com>
# SPDX-License-Identifier: BSD-2-Clause


from migen import ClockDomain, ClockDomainsRenamer, Display, FSM, If, Module, Signal

# ------------------------------------------------------------------------------------------------ #
#                                       SIMULATION                                                 #
# ------------------------------------------------------------------------------------------------ #

# Stub for $time in Display()/Monitor() args -------------------------------------------------------

class Time:
    """Expression for $time in Display()/Monitor() statements
    
    Example:
    self.sync += If(state != old_state,
        Display("time=%t old_state: %d state: %d", Time(), old_state, state)
    )
    """
    pass

class Cycles(Module):
    def __init__(self, cd_name="sys", nbits=64) -> None:
        class ClockDomainCounter(Module):
            def __init__(self) -> None:
                self.count = Signal(nbits)
                self.sync += self.count.eq(self.count + 1)
        self.submodules.cd_counter = ClockDomainsRenamer(cd_name)(ClockDomainCounter())
        self.count = self.cd_counter.count

# Wraps a Signal with metadata, e.g. on_change -----------------------------------------------------
class MonitorArg:
    def __init__(self, signal, name=None, fmt=None, on_change=True):
        self.signal = signal
        self.name = name
        self.fmt = fmt
        self.on_change = on_change


# $monitor() ---------------------------------------------------------------------------------------
class Monitor(Module):
    """
    Monitor("tx_data: %0b rx_data: %0b", tx_data, rx_data)
    Monitor("tick: %0d tx_data: {txd} rx_data: %0b",
        MonitorArg(nclks, on_change=False),
        MonitorArg(tx_data, "txd", "%0b"),
        rx_data,
    )
    """

    def __init__(self, fmt, *args):
        arg_sigs = []
        monitored_sigs = []
        fmt_replacements = {}
        for arg in args:
            if isinstance(arg, MonitorArg):
                arg_sigs.append(arg.signal)
                if arg.fmt is not None:
                    fmt_replacements[arg.name] = arg.fmt
                if arg.on_change and isinstance(arg.signal, Signal):
                    monitored_sigs.append(arg.signal)
            else:
                arg_sigs.append(arg)
            if isinstance(arg, Signal):
                monitored_sigs.append(arg)
        fmt = fmt.format(**fmt_replacements)

        old_vals = {sig: Signal.like(sig) for sig in monitored_sigs}
        changed = Signal()

        self.comb += changed.eq(0)
        for sig, old_sig in old_vals.items():
            self.sync += old_sig.eq(sig)
            self.comb += changed.eq(changed | (old_sig != sig))

        self.sync += If(changed, Display(fmt, *arg_sigs))


class DisplaySync(Display):
    pass


class DisplayEnter(Display):
    pass


class MonitorFSM(FSM):
    pass

class MonitorFSMState(Module):
    def __init__(self, fsm, description="", ticks=False, time=False):
        fmt = ""
        args = []
        if time:
            fmt += "time: %0d "
            args.append(Time())
        if ticks:
            fmt += "tick: %0d "
            nclks = Signal(64)
            self.sync += nclks.eq(nclks + 1)
            args.append(nclks)
        fmt += description
        for state in fsm.actions.keys():
            fsm.act(state, DisplayEnter(f"{fmt} entered {state}", *args))