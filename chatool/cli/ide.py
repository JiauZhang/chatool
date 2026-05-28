import os
import argparse
from pathlib import Path
import chatool

IDE_CONFIGS = {
    'trae': {
        'rules': '~/.trae-cn/rules',
        'skills': '~/.trae-cn/skills',
    },
    'codebuddy': {
        'rules': '~/.codebuddy/rules',
        'skills': '~/.codebuddy/skills',
    },
}


def get_source_dirs():
    pkg_dir = Path(chatool.__file__).parent.resolve()
    return pkg_dir / 'rules', pkg_dir / 'skills'


def link(targets):
    rules_src, skills_src = get_source_dirs()

    for target in targets:
        config = IDE_CONFIGS[target]
        for name, src in [('rules', rules_src), ('skills', skills_src)]:
            dst = Path(config[name]).expanduser()
            src_str = str(src)

            if dst.is_symlink():
                if os.readlink(str(dst)) == src_str:
                    print(f'SKIP {dst} -> {src_str} (already linked)')
                    continue
                print(f'ERROR {dst} exists but points elsewhere, remove it first')
                continue

            if dst.exists():
                if dst.is_dir() and not any(dst.iterdir()):
                    dst.rmdir()
                else:
                    print(f'ERROR {dst} already exists and is not empty, remove it first')
                    continue

            dst.parent.mkdir(parents=True, exist_ok=True)
            os.symlink(src_str, str(dst))
            print(f'LINKED {dst} -> {src_str}')


def unlink(targets):
    rules_src, skills_src = get_source_dirs()

    for target in targets:
        config = IDE_CONFIGS[target]
        for name, src in [('rules', rules_src), ('skills', skills_src)]:
            dst = Path(config[name]).expanduser()
            src_str = str(src)

            if not dst.is_symlink():
                if dst.exists():
                    print(f'SKIP {dst} (not a symlink, not removing)')
                else:
                    print(f'SKIP {dst} (not found)')
                continue

            if os.readlink(str(dst)) != src_str:
                print(f'SKIP {dst} (does not point to chatool)')
                continue

            dst.unlink()
            print(f'UNLINKED {dst}')


def list_status():
    rules_src, skills_src = get_source_dirs()

    for ide_name, config in IDE_CONFIGS.items():
        for name, src in [('rules', rules_src), ('skills', skills_src)]:
            dst = Path(config[name]).expanduser()
            src_str = str(src)

            if dst.is_symlink():
                target = os.readlink(str(dst))
                status = 'linked' if target == src_str else f'linked (wrong target: {target})'
            elif dst.exists():
                status = 'exists (not a symlink)'
            else:
                status = 'not found'
            print(f'{ide_name:6s} {name:6s} -> {status}')


def main(argv=None):
    parser = argparse.ArgumentParser(prog='chatool ide')
    parser.add_argument('--list', action='store_true', help='List current symlink status')

    sub = parser.add_subparsers(dest='command', title='available commands', metavar='{link,unlink,list}')

    link_parser = sub.add_parser('link', help='Create symlinks for IDE skills/rules')
    link_parser.add_argument(
        '--target', nargs='+', choices=['qoder', 'trae', 'all'], default=['all'],
    )

    unlink_parser = sub.add_parser('unlink', help='Remove symlinks for IDE skills/rules')
    unlink_parser.add_argument(
        '--target', nargs='+', choices=['qoder', 'trae', 'all'], default=['all'],
    )

    sub.add_parser('list', help='List current symlink status')

    args = parser.parse_args(argv)

    if args.list:
        list_status()
    elif args.command in ('link', 'unlink'):
        targets = args.target
        if 'all' in targets:
            targets = list(IDE_CONFIGS.keys())
        else:
            targets = list(dict.fromkeys(targets))

        if args.command == 'link':
            link(targets)
        else:
            unlink(targets)
    elif args.command == 'list':
        list_status()
