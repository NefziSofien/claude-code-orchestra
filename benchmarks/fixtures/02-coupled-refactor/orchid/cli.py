"""Command line entry point: python3 -m orchid.cli <config-file>."""
import sys

from orchid.config import parse_config
from orchid.loader import load


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: orchid.cli <config-file>", file=sys.stderr)
        return 2
    cfg = parse_config(argv[0])
    _, active = load(argv[0])
    print(f"{cfg['name']}: {', '.join(active)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
