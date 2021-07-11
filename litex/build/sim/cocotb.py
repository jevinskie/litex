#
# This file is part of LiteX.
#
# Copyright (c) 2015-2019 Florent Kermarrec <florent@enjoy-digital.fr>
# Copyright (c) 2017 Pierre-Olivier Vauboin <po@lambdaconcept>
# Copyright (c) 2021 Jevin Sweval <jevinsweval@gmail.com>
# SPDX-License-Identifier: BSD-2-Clause

from pathlib import Path
import os
import sys
import subprocess
from shutil import which

from migen.fhdl.structure import _Fragment
from litex import get_data_mod
from litex.build import tools
from litex.build.generic_platform import *

import rpyc
from rpyc.core.service import ClassicService
from rpyc.utils.server import ThreadedServer


def _generate_sim_makefile(build_dir: str, build_name: str, sources: list[str], module):
    assert all([lambda src: src[1] == "verilog"])

    module_dir = Path(module.__file__).parent

    makefile_contents = f"""
SIM = icarus
TOPLEVEL_LANG = verilog

VERILOG_SOURCES += {' '.join(map(lambda src: src[0], sources))}

# TOPLEVEL is the name of the toplevel module in your Verilog or VHDL file
TOPLEVEL = {build_name}

# MODULE is the basename of the Python test file
MODULE = {build_name}

export PYTHONPATH := {module_dir}:$(PTYHONPATH):{':'.join(sys.path)}

DUMP_VCD = 1

# include cocotb's make rules to take care of the simulator setup
include $(shell cocotb-config --makefiles)/Makefile.sim

"""
    tools.write_to_file("Makefile", makefile_contents, force_unix=True)

def _run_sim(build_name: str):
    socket_path = f'{build_name}.pipe'
    try:
        os.remove(socket_path)
    except  FileNotFoundError:
        pass
    server = ThreadedServer(ClassicService, socket_path=socket_path, auto_register=False)
    # self.server.logger.quiet = False
    server._start_in_thread()
    try:
        r = subprocess.call(["make"])
        if r != 0:
            raise OSError("Subprocess failed")
    except:
        pass

class SimCocotbToolchain:
    def build(self, platform, fragment, module,
            build_dir    = "build",
            build_name   = "cocotb",
            build        = True,
            run          = False,
            threads      = 1,
            verbose      = True,
            sim_config   = None,
            coverage     = False,
            opt_level    = "O0",
            trace        = False,
            trace_fst    = False,
            trace_start  = 0,
            trace_end    = -1,
            trace_exit   = False,
            sim_end      = -1,
            regular_comb = False):

        # Create build directory
        os.makedirs(build_dir, exist_ok=True)
        cwd = os.getcwd()
        os.chdir(build_dir)

        if build:
            # Finalize design
            if not isinstance(fragment, _Fragment):
                fragment = fragment.get_fragment()
            platform.finalize(fragment)

            # Generate verilog
            v_output = platform.get_verilog(fragment,
                name            = build_name,
                dummy_signal    = False,
                regular_comb    = regular_comb,
                blocking_assign = True)
            named_sc, named_pc = platform.resolve_signals(v_output.ns)
            v_file = build_name + ".v"
            v_output.write(v_file)
            platform.add_source(v_file)

            # Generate cocotb makefile
            _generate_sim_makefile(build_dir, build_name, platform.sources, module)

        # Run
        if run:
            _run_sim(build_name)

        os.chdir(cwd)

        if build:
            return v_output.ns
