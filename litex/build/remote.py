import os
import sys
import tempfile
from pathlib import Path
import socket
import subprocess
import time

import rpyc
from rpyc.core.service import ClassicService
from rpyc.utils.server import ThreadPoolServer

class BuildService(rpyc.Service):
    exposed_platform = None

class BuildServer:
    def __init__(self, socket_path: Path):
        self.socket_path = socket_path
        self.srv = ThreadPoolServer(BuildService, socket_path=str(socket_path), protocol_config={"allow_all_attrs": True})
        self.srv_inst = rpyc.lib.spawn(lambda: self.srv.start())

    def join(self):
        self.srv_inst.join()

def _getenv_checked(var):
    val = os.getenv(var)
    if val is None:
        raise KeyError(f"environment variable '{var}' is not defined")
    return val

def get_remote_host(host):
    if host is not None:
        return host
    return _getenv_checked("LITEX_REMOTE_BUILD_HOST")

def get_remote_user(user):
    if user is not None:
        return user
    return os.getenv("LITEX_REMOTE_BUILD_USER")

class RemoteContext:
    def __init__(self, host=None, user=None):
        self.host = get_remote_host(host)
        self.user = get_remote_user(user)
        self.socket_path = Path(tempfile.mktemp(prefix='litex-remote-rpyc-sock-', suffix=".sock", dir="/tmp"))
        user_host_arg = self.host
        if self.user:
            user_host_arg = f"{self.user}@{self.host}"
        fwd_args = ["-L", f"{self.socket_path}:{self.socket_path}"]
        py_cmd =  " ".join(["python3", "-m", "litex.tools.litex_remote_build", "--serve", str(self.socket_path)])
        self.args = ["ssh", *fwd_args, user_host_arg, "sh", "-l", "-c", f"'{py_cmd}'"]

    def start_remote_server(self):
        self.ssh_proc = subprocess.Popen(self.args)
        print(f"wait: {self.socket_path}")
        while not os.path.exists(self.socket_path):
            time.sleep(0.010)
        time.sleep(1)
        print(f"connect: {self.socket_path}")
        self.rpyc = rpyc.utils.factory.unix_connect(str(self.socket_path))


    def close(self):
        self.ssh_proc.wait()
        self.ssh_proc = None

def run_build_server_remotely(host=None, user=None):
    rc = RemoteContext(host, user)
    rc.start_remote_server()
    print(rc.rpyc)
    print(rc.rpyc.ping())
    rc.close()
    print("after run")


def run_build_server(socket_path):
    print(f"serving on {socket_path}")
    build_server = BuildServer(socket_path)
    print("build server started")
    build_server.join()
    print("build server joined")
