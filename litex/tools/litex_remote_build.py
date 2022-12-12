#!/usr/bin/env python3

#
# This file is part of LiteX.
#
# Copyright (c) 2022 Jevin Sweval <jevinsweval@gmail.com>
# SPDX-License-Identifier: BSD-2-Clause

import argparse
import fcntl
import sys
import termios

from litex.build.remote import run_build_server, run_build_server_remotely

# Test Dummy ---------------------------------------------------------------------------------------
import os
from litex.build.remote import run_remote
# @run_remote()
def _print_os_uname():
    print(os.uname())

# Run ----------------------------------------------------------------------------------------------

def _get_args():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--serve", action="store_true", help="run the LiteX build server")
    parser.add_argument("--sock-path", help="RPyC socket path")
    parser.add_argument("--sync-path", help="syncronization socket path")
    parser.add_argument("--remote-serve", action="store_true", help="run the LiteX build server remotely")
    parser.add_argument("--host", help="remote build server hostname")
    parser.add_argument("--user", help="remote build server username")
    return parser.parse_args()

def main():
    args = _get_args()
    if args.serve:
        if args.sock_path is None:
            raise ValueError("--sock-path must be specified")
        if args.sync_path is None:
            raise ValueError("--sync-path must be specified")
        term_attr = termios.tcgetattr(sys.stdin.fileno())
        term_flags = fcntl.fcntl(sys.stdin.fileno(), fcntl.F_GETFL)
        try:
            run_build_server(args.sock_path, args.sync_path)
        except Exception as e:
            print(f"run_build_server() failed:\n{e}")
        termios.tcsetattr(sys.stdin.fileno(), termios.TCSAFLUSH, term_attr)
        fcntl.fcntl(sys.stdin.fileno(), fcntl.F_SETFL, term_flags)
    elif args.remote_serve:
        try:
            run_build_server_remotely(args.host, user=args.user)
        except Exception as e:
            print(f"run_build_server_remotely() failed:\n{e}")

if __name__ == "__main__":
    main()
