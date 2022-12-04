import os

import rpyc
from rpyc.core.service import ClassicService
from rpyc.utils.server import ThreadPoolServer
import sysrsync
import fabric

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

def run_remote(host, args, user=None, pty=False):
    host = get_remote_host(host)
    user = get_remote_user(user)
    conn = fabric.Connection(host, user)
    term = os.getenv("TERM", "vt100")
    conn.run(f"env TERM={term} " + " ".join(args), pty=pty)

def run_build_server(host, user=None):
    host = get_remote_host(host)
    user = get_remote_user(user)
    # run_remote(host, , user=None, pty=False)
