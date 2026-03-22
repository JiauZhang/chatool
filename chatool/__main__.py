import sys, runpy
from pathlib import Path

def list_tools():
    tools_dir = Path(__file__).parent / 'tools'
    tools = [f.stem for f in tools_dir.glob('*.py') if not f.name.startswith('_')]
    print('Available tools:')
    for tool in sorted(tools):
        print(f'  {tool}')

def main():
    if len(sys.argv) < 2:
        print('Usage: chatool <tool> [args...]')
        print('       chatool --list')
        sys.exit(1)
    if sys.argv[1] == '--list':
        list_tools()
        return
    tool = sys.argv[1]
    sys.argv = [tool] + sys.argv[2:]
    runpy.run_module(f'chatool.tools.{tool}', run_name='__main__')

if __name__ == '__main__':
    main()
