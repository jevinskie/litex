import argparse
import time

from litex.build.remote import run_remote, run_build_server, run_build_server_remotely

# Run ----------------------------------------------------------------------------------------------

def _get_args():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--run", nargs=argparse.REMAINDER, help="run command on remote node")
    parser.add_argument("--pty", action="store_true", help="pty mode (act like a real terminal)")
    parser.add_argument("--serve", action="store_true", help="run the LiteX build server")
    parser.add_argument("--remote-serve", action="store_true", help="run the LiteX build server remotely")
    parser.add_argument("--host", help="remote build server hostname")
    parser.add_argument("--user", help="remote build server username")
    return parser.parse_args()

def main():
    args = _get_args()
    if args.run is not None:
        run_remote(args.host, args.run, user=args.user, pty=args.pty)
    elif args.serve:
        run_build_server()
        print("sleeping")
        time.sleep(60)
        print("exiting")
    elif args.remote_serve:
        run_build_server_remotely(args.host, user=args.user)

if __name__ == "__main__":
    main()