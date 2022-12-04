import argparse

from litex.build.remote import *

# Run ----------------------------------------------------------------------------------------------

def _get_args():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--run", nargs=argparse.REMAINDER, help="run command on remote node")
    return parser.parse_args()

def main():
    args = _get_args()


if __name__ == "__main__":
    main()