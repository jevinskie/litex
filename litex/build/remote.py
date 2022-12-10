import os
import tempfile
from pathlib import Path
import socket
import subprocess
import time

import rpyc
from rpyc.utils.server import ThreadPoolServer

class BuildService(rpyc.Service):
    exposed_platform = None
    exposed_soc = None
    exposed_ns = None

    def exposed_call_on_server(self, func):
        return func(self.exposed_platform, self.exposed_soc, self.exposed_ns)

class BuildServer:
    def __init__(self, socket_path: Path, sync_path: Path):
        self.socket_path = socket_path
        self.sync_path = sync_path
        self.srv = ThreadPoolServer(BuildService, socket_path=str(socket_path), protocol_config={"allow_all_attrs": True})
        self.srv_thread = rpyc.lib.spawn(lambda: self.srv.start())
        self.sync_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sync_sock.connect(self.sync_path)
        self._send_sync_start()

    def _send_sync_start(self):
        self.sync_sock.sendall(b"start")

    def serve_and_close(self):
        sync_msg = self.sync_sock.recv(4)
        assert sync_msg == b"stop"
        self.sync_sock.sendall(b"dead")
        self.sync_sock.close()
        self.srv.close()
        self.srv_thread.join()

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
        # we assume the temp file name chosen for the client is also valid on the server
        # probably needs fixing for Windows
        self.socket_path = Path(tempfile.mktemp(prefix='litex-remote-rpyc-sock-', suffix=".sock", dir="/tmp"))
        # use an out-of-band (w.r.t. RPyC) connection to synchronize RPyC start/stop
        # 1) prevents client from receiving from RPyC socket before server has started serving on socket
        # 2) rpyc.core.protocol.Connection can't be closed easily from client
        #    Instead server blocks waiting for client to send b"stop" over sync socket before calling
        #    rpyc_conn.close() itself
        self.sync_path = Path(tempfile.mktemp(prefix='litex-remote-rpyc-sync-', suffix=".sock", dir="/tmp"))
        user_host_arg = self.host
        if self.user:
            user_host_arg = f"{self.user}@{self.host}"
        fwd_args = ["-L", f"{self.socket_path}:{self.socket_path}", "-R", f"{self.sync_path}:{self.sync_path}"]
        py_cmd =  " ".join(["python3", "-m", "litex.tools.litex_remote_build", "--serve", "--sock-path", str(self.socket_path), "--sync-path", str(self.sync_path)])
        # use a login shell so we pick up any .profile type env-vars
        self.args = ["ssh", "-t", *fwd_args, user_host_arg, "sh", "-l", "-c", f"'{py_cmd}'"]

    def start_remote_server(self):
        self.ssh_proc = subprocess.Popen(self.args)
        # it can take some time for ssh to begin forwarding
        while not self.socket_path.exists() and not self.sync_path.exists():
            time.sleep(0.010)
        self._wait_for_sync_start()
        self.rpyc_conn = rpyc.utils.factory.unix_connect(str(self.socket_path))

    def _wait_for_sync_start(self):
        self.sync_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sync_sock.bind(str(self.sync_path))
        self.sync_sock.listen(1)
        self.sync_conn, _ = self.sync_sock.accept()
        sync_msg = self.sync_conn.recv(5)
        assert sync_msg == b"start"

    def close(self):
        self.sync_conn.sendall(b"stop")
        sync_msg = self.sync_conn.recv(4)
        assert sync_msg == b"dead"
        # ssh won't exit until all forwarded sockets are closed
        self.sync_conn.close()
        self.sync_sock.close()
        self.rpyc_conn.close()
        self.ssh_proc.wait()

def run_build_server_remotely(host=None, user=None):
    rc = RemoteContext(host, user)
    rc.start_remote_server()
    rc.rpyc_conn.ping()
    rc.close()

def run_build_server(socket_path, sync_path):
    print(f"LiteX build server serving on: {socket_path} sync: {sync_path}")
    build_server = BuildServer(socket_path, sync_path)
    print("LiteX build server started")
    build_server.serve_and_close()
    print("LiteX build server closed")
