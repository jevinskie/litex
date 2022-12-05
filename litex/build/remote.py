import os
import sys

import fabric
import rpyc
import sysrsync
from rpyc.core.service import ClassicService
from rpyc.utils.server import ThreadPoolServer


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
    conn.run(" ".join(args), **kwargs)


def run_build_server_remotely(host, user=None):
    host = get_remote_host(host)
    user = get_remote_user(user)
    conn = fabric.Connection(host, user)
    run_kwargs = dict(pty=True, err_stream=sys.stderr, out_stream=sys.stdout)
    prom = conn.run("sh -l -c 'litex_remote_build --serve'", asynchronous=True, **run_kwargs)
    print("after run")
    res = prom.join()

def run_build_server():
    print("serving")
