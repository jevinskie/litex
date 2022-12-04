import argparse

from litex.build.remote import run_build_server, run_remote

# Run ----------------------------------------------------------------------------------------------

def _get_args():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--run", nargs=argparse.REMAINDER, help="run command on remote node")
    parser.add_argument("--pty", action="store_true", help="pty mode (act like a real terminal)")
    parser.add_argument("--serve", action="store_true", help="run the LiteX build server")
    parser.add_argument("--host", help="remote build server hostname")
    parser.add_argument("--user", help="remote build server username")
    return parser.parse_args()

def main():
    args = _get_args()
    if args.run is not None:
        run_remote(args.host, args.run, user=args.user, pty=args.pty)
    elif args.serve:
        run_build_server()

if __name__ == "__main__":
    main()