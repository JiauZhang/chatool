import argparse

from chatool.cli.ide import main as ide_main


def main():
    parser = argparse.ArgumentParser(prog='chatool', add_help=False)
    sub = parser.add_subparsers(dest='command')
    sub.add_parser('ide', add_help=False, help='Manage IDE skills/rules symlinks')

    args, remaining = parser.parse_known_args()
    if args.command == 'ide':
        ide_main(remaining)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
