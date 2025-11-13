import argparse
import sys
from ..gate.formal_gate import check_formal_file_json


def main():
    parser = argparse.ArgumentParser(prog="pudao")
    subparsers = parser.add_subparsers(dest="command")

    formal_parser = subparsers.add_parser("formal", help="Formal verification tools")
    formal_sub = formal_parser.add_subparsers(dest="formal_cmd")

    check_parser = formal_sub.add_parser("check", help="Run SMT formal check on a strategy file")
    check_parser.add_argument("-f", "--file", required=True, help="Path to strategy yaml/json")

    args = parser.parse_args()

    if args.command == "formal" and args.formal_cmd == "check":
        out = check_formal_file_json(args.file)
        print(out)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
