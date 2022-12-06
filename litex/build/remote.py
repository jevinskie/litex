import os
import sys
import tempfile
from pathlib import Path
import socket

import fabric
import rpyc
import sysrsync
from rpyc.core.service import ClassicService
from rpyc.utils.server import ThreadPoolServer

def ssh(host, *args, user=None, pty=False):
    pass

def _getenv(var):
    val = os.getenv(var)
    if val is None:
        raise KeyError(f"environment variable '{var}' is not defined")
    return val

def get_remote_host(host):
    if host is not None:
        return host
    return _getenv("LITEX_REMOTE_BUILD_HOST")

def get_remote_user(user):
    if user is not None:
        return user
    return os.getenv("LITEX_REMOTE_BUILD_USER")

def run_remote(host, args, user=None, pty=False, **kwargs):
    host = get_remote_host(host)
    user = get_remote_user(user)
    conn = fabric.Connection(host, user)
    kwargs.update(pty=pty, err_stream=sys.stderr, out_stream=sys.stdout)
    term = os.getenv("TERM", "vt100")
    conn.run(f"env TERM={term} " + " ".join(args), **kwargs)


class RemoteContext:
    def __init__(self, host=None, user=None):
        self.host = get_remote_host(host)
        self.user = get_remote_user(user)
        self.conn = fabric.Connection(self.host, self.user)
        self.sock_path = Path(tempfile.mkdtemp(prefix='litex-remote-', dir="/tmp")) / "rpyc.sock"
        self.conn.transport.request_port_forward()


def run_build_server_remotely(host, user=None):
    host = get_remote_host(host)
    user = get_remote_user(user)
    conn = fabric.Connection(host, user)
    run_kwargs = dict(pty=True, err_stream=sys.stderr, out_stream=sys.stdout)
    term = os.getenv("TERM", "vt100")
    sock_path = Path(tempfile.mkdtemp(prefix='litex-remote-', dir="/tmp")) / "rpyc.sock"
    conn.create_session()
    conn.transport.request_port_forward(sock_path)
    prom = conn.run(f"env TERM={term} sh -l -c 'litex_remote_build --serve {sock_path}'", asynchronous=True, **run_kwargs)
    print("after run")
    res = prom.join()

def run_build_server(domain_socket_path):
    print(f"serving: domain socket: {domain_socket_path}")
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    print("binding", file=sys.stderr)
    sock.bind(domain_socket_path)
    sock.listen(1)
    con, addr = sock.accept()
    print(f"con: {con} addr: {addr}")
