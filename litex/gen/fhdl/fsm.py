#
# This file is part of LiteX.
#
# Copyright (c) 2021 Jevin Sweval <jevinsweval@gmail.com>
# SPDX-License-Identifier: BSD-2-Clause

from collections import OrderedDict

from migen.genlib.fsm import FSM

class CorrectedResetFSM(FSM):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ongoing_signals = OrderedDict()

    def ongoing(self, state, *args, **kwargs):
        is_ongoing = super().ongoing(state, *args, **kwargs)
        self.ongoing_signals[state] = is_ongoing
        return is_ongoing

    def do_finalize(self, *args, **kwargs):
        for state, is_ongoing in self.ongoing_signals.items():
            is_ongoing.reset = 1 if state == self.reset_state else 0
            if is_ongoing.reset.value:
                # since the default is high, explicitly deassert in all other states
                for other_state in set(self.actions) - set([state]):
                    self.actions[other_state].append(is_ongoing.eq(0))
        super().do_finalize(*args, **kwargs)
