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
from rpyc.utils.server import ThreadedServer, ThreadPoolServer

import cocotb


pydev_host = os.environ.get('PYDEV_HOST', None)
pydev_port = os.environ.get('PYDEV_PORT', None)

if pydev_port is not None:
    import pydevd
    pydevd.settrace(pydev_host, port=int(pydev_port), suspend=False)


class SimService(rpyc.Service):
    exposed_platform = None
    exposed_soc = None
    exposed_ns = None

    def exposed_call_on_server(self, func):
        res = None
        res = func(self.exposed_platform, self.exposed_soc, self.exposed_ns)
        return res


class SimServer:
    def __init__(self, socket_path: str):
        self.socket_path = socket_path
        try:
            os.remove(socket_path)
        except  FileNotFoundError:
            pass
        self.srv = ThreadPoolServer(SimService, socket_path=socket_path, protocol_config={"allow_all_attrs": True})
        rpyc.lib.spawn(lambda: self.srv.start())

    def __del__(self):
            self.srv.close()
            os.remove(self.socket_path)


def start_sim_server(socket_path=None):
    if cocotb.top is None and socket_path is None:
        return
    elif socket_path is not None:
        server = SimServer(socket_path)
        return server
    elif cocotb.top is not None and socket_path is None:
        socket_path = f'{os.environ["MODULE"]}.pipe'
        return rpyc.utils.factory.unix_connect(socket_path)
    else:
        raise RuntimeError


def _generate_sim_makefile(build_dir: str, build_name: str, sources: list[str], module, sim_top = None):
    assert all([lambda src: src[1] == "verilog"])

    toplevel = build_name
    if sim_top:
        toplevel = sim_top.stem
        sources.append((str(sim_top), "verilog"))

    module_dir = Path(module.__file__).parent

    makefile_contents = f"""
SIM = icarus
TOPLEVEL_LANG = verilog

VERILOG_SOURCES += {' '.join(map(lambda src: src[0], sources))}

# TOPLEVEL is the name of the toplevel module in your Verilog or VHDL file
TOPLEVEL = {toplevel}

# MODULE is the basename of the Python test file
MODULE = {build_name}

export PYTHONPATH := {module_dir}:$(PTYHONPATH):{':'.join(sys.path)}

DUMP_VCD = 1

# include cocotb's make rules to take care of the simulator setup
include $(shell cocotb-config --makefiles)/Makefile.sim

"""
    tools.write_to_file("Makefile", makefile_contents, force_unix=True)


def _run_sim(build_name: str, platform, soc, namespace):
    socket_path = f'{build_name}.pipe'
    local_sim_server = start_sim_server(socket_path)
    local_sim_server.srv.service.exposed_platform = platform
    local_sim_server.srv.service.exposed_soc = soc
    local_sim_server.srv.service.exposed_ns = namespace
    try:
        import pydevd
        pydevd_setup = pydevd.SetupHolder.setup
        if pydevd_setup is not None:
            host, port = pydevd.dispatch()
            os.environ['PYDEV_HOST'] = host
            os.environ['PYDEV_PORT'] = str(port)
            print(f'set environ to host: {host} port: {port}')
    except ImportError:
        pass
    try:
        r = subprocess.call(["make"])
        if r != 0:
            raise OSError("Subprocess failed")
    except:
        pass
    # stop_sim_server(local_sim_server)


class SimCocotbToolchain:
    def build(self, platform, fragment,
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
            sim_top      = None,
            regular_comb = False,
            module       = None,
            soc          = None):


        if sim_top:
            sim_top = Path(sim_top)
            sim_top = sim_top.resolve()

        # Create build directory
        os.makedirs(build_dir, exist_ok=True)
        cwd = os.getcwd()
        os.chdir(build_dir)

        # Finalize design
        if not isinstance(fragment, _Fragment):
            fragment = fragment.get_fragment()
        platform.finalize(fragment)

        # Generate verilog
        v_output = platform.get_verilog(fragment,
            name            = build_name,
            dummy_signal    = True,
            regular_comb    = False,
            blocking_assign = True)
        named_sc, named_pc = platform.resolve_signals(v_output.ns)
        v_file = build_name + ".v"

        if build:
            v_output.write(v_file)
            platform.add_source(v_file)

            # Generate cocotb makefile
            _generate_sim_makefile(build_dir, build_name, platform.sources, module, sim_top)

        # Run
        if run:
            _run_sim(build_name, platform, soc, v_output.ns)

        os.chdir(cwd)

        if build:
            return v_output.ns
