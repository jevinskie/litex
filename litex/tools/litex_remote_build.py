import argparse
import time

from litex.build.remote import run_build_server, run_build_server_remotely

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
        run_build_server(args.sock_path, args.sync_path)
    elif args.remote_serve:
        run_build_server_remotely(args.host, user=args.user)

if __name__ == "__main__":
    main()