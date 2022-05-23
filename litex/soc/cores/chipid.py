#
# This file is part of LiteX.
#
# Copyright (c) 2022 Jevin Sweval <jevinsweval@gmail.com>
# SPDX-License-Identifier: BSD-2-Clause

import os

from migen import *
from migen.genlib.misc import WaitTimer
from litex.soc.interconnect.csr import *


class AlteraChipID(Module, AutoCSR):
    def __init__(self):
        self.regout   = CSRStatus()
        self.chip_id  = CSRStatus(64)
        self.valid    = CSRStatus()
        self.go       = CSRStorage()
        self.shiftnld = Signal()
        self.done     = Signal()
        self.wait     = Signal()

        self.submodules.valid_timer = WaitTimer(64)

        self.sync += If(self.shiftnld,
            self.chip_id.status.eq(Cat(self.chip_id.status[1:], self.regout.status))
        )

        self.comb += [
            self.valid_timer.wait.eq(0),
            self.done.eq(self.valid_timer.done),
            self.wait.eq(self.valid_timer.wait),
            self.valid.status.eq(self.valid_timer.done),
            self.valid_timer.wait.eq(self.go.storage),
            self.shiftnld.eq(~self.valid_timer.done & self.valid_timer.wait),
        ]

        self.specials += Instance("fiftyfivenm_chipidblock", "chipid",
            i_clk      = ClockSignal("sys"),
            i_shiftnld = self.shiftnld,
            o_regout   = self.regout.status,
        )

# For verification, delete before merge
class AlteraChipIDIP(Module, AutoCSR):
    def __init__(self, platform):
        self.reset = CSRStorage()
        self.chip_id = CSRStatus(64)
        self.valid   = CSRStatus()

        self.specials += Instance("altchip_id", "chipid",
            i_clkin      = ClockSignal("sys"),
            i_reset      = self.reset.storage,
            o_data_valid = self.valid.status,
            o_chip_id    = self.chip_id.status,
            p_DEVICE_FAMILY = "MAX 10"
        )

        platform.add_source(os.path.join(
            platform.toolchain.ip_dir, "altera", "altchip_id", "source", "altchip_id.v"
        ))
