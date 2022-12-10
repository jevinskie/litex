import os
import sys
import tempfile
from pathlib import Path
import socket
import subprocess
import time
import syslog

import rpyc
from rpyc.core.service import ClassicService
from rpyc.utils.server import ThreadPoolServer
# from rich import print

orig_print = print
def print(*args, **kwargs):
    orig_print(*args, **kwargs)
    syslog.syslog(syslog.LOG_INFO, format(*args))

class BuildService(rpyc.Service):
    exposed_serv = None
    exposed_platform = None
    exposed_soc = None
    exposed_ns = None

    def exposed_close(self):
        self.exposed_serv.close()

    def exposed_call_on_server(self, func):
        return func(self.exposed_serv, self.exposed_platform, self.exposed_soc, self.exposed_ns)

    def on_connect(self, conn):
        print(f"BuildService connect {conn}")

    def on_disconnect(self, conn):
        print(f"BuildService disconnect {conn}")
        # assert False == True
        # os.kill(os.getpid())
        # os._exit()
        # exposed_close()

class BuildServer:
    def __init__(self, socket_path: Path, sync_path: Path):
        self.socket_path = socket_path
        self.sync_path = sync_path
        self.srv = ThreadPoolServer(BuildService, socket_path=str(socket_path), protocol_config={"allow_all_attrs": True})
        self.srv.service.exposed_serv = self.srv
        print("bs spawning")
        self.srv_inst = rpyc.lib.spawn(lambda: self.srv.start())
        print("bs spawned")
        self.sync_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sync_sock.connect(self.sync_path)
        self._send_sync_start()

    def _send_sync_start(self):
        self.sync_sock.sendall(b"start")

    def join(self):
        print(f"BuildServer join()\n{self.srv_inst}")
        sync_msg = self.sync_sock.recv(4)
        assert sync_msg == b"stop"
        print("sending dead")
        self.sync_sock.sendall(b"dead")
        print("closing")
        self.sync_sock.close()
        print("sock closed")
        self.srv.close()
        print("srv closed")
        self.srv_inst.join()
        print("srv thread joined")
        pass 

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
        self.sync_path = Path(tempfile.mktemp(prefix='litex-remote-rpyc-sync-', suffix=".sock", dir="/tmp"))
        user_host_arg = self.host
        if self.user:
            user_host_arg = f"{self.user}@{self.host}"
        fwd_args = ["-L", f"{self.socket_path}:{self.socket_path}", "-R", f"{self.sync_path}:{self.sync_path}"]
        py_cmd =  " ".join(["python3", "-m", "litex.tools.litex_remote_build", "--serve", "--sock-path", str(self.socket_path), "--sync-path", str(self.sync_path)])
        # py_cmd = "/usr/bin/env false"
        self.args = ["ssh", "-vvv", "-t", *fwd_args, user_host_arg, "sh", "-x", "-l", "-c", f"'{py_cmd}; exit'"]

    def start_remote_server(self):
        print(f"running: {' '.join(self.args)}")
        self.ssh_proc = subprocess.Popen(self.args)
        print(f"wait: {self.socket_path}")
        while not os.path.exists(self.socket_path) and not os.path.exists(self.sync_path):
            time.sleep(0.010)
        self._wait_for_sync_start()
        print(f"connect: {self.socket_path}")
        self.rpyc = rpyc.utils.factory.unix_connect(str(self.socket_path))

    def _wait_for_sync_start(self):
        self.sync_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sync_sock.bind(str(self.sync_path))
        self.sync_sock.listen(1)
        self.conn, _ = self.sync_sock.accept()
        sync_msg = self.conn.recv(5)
        print(f"{socket.gethostname()} got {sync_msg}")
        assert sync_msg == b"start"

    def close(self):
        self.conn.sendall(b"stop")
        sync_msg = self.conn.recv(4)
        assert sync_msg == b"dead"
        self.conn.close()
        self.sync_sock.close()
        print("close/ssh_proc wait")
        self.rpyc.close()
        self.ssh_proc.wait()
        self.ssh_proc = None

def run_build_server_remotely(host=None, user=None):
    rc = RemoteContext(host, user)
    rc.start_remote_server()
    print(rc.rpyc)
    print(rc.rpyc.ping())
    # print("rpyc close")
    # print(rc.rpyc.root.close())
    print("local close 1")
    # rc.rpyc.close()
    print("local close 2")
    rc.close()
    print("after run")


def run_build_server(socket_path, sync_path):
    print(f"serving on {socket_path} sync: {sync_path}")
    build_server = BuildServer(socket_path, sync_path)
    print("build server started")
    build_server.join()
    print("build server joined")
