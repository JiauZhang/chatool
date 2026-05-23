import re
from conippets import json
from conippets.shell import Shell
from chatchat.tool import tool


_DANGEROUS_PATTERNS = [
    # 删除/覆盖系统关键路径
    re.compile(r'\brm\s+(-[rf]+|[rf]+)', re.IGNORECASE),
    re.compile(r'\bmv\s+/\s+'),
    # 特权执行
    re.compile(r'\bsudo\b'),
    # 磁盘/分区操作
    re.compile(r'\bdd\b'),
    re.compile(r'\bmkfs\.'),
    re.compile(r'\bfdisk\b'),
    re.compile(r'\bparted\b'),
    # 系统控制
    re.compile(r'\bshutdown\b'),
    re.compile(r'\breboot\b'),
    re.compile(r'\bhalt\b'),
    re.compile(r'\bpoweroff\b'),
    # 递归修改权限
    re.compile(r'\bchmod\s+-R', re.IGNORECASE),
    re.compile(r'\bchown\s+-R', re.IGNORECASE),
    # 下载并执行
    re.compile(r'\bcurl\s+.*\b(bash|sh)\b', re.IGNORECASE),
    re.compile(r'\bwget\s+.*\b(bash|sh)\b', re.IGNORECASE),
    # 写入系统关键文件
    re.compile(r'>\s*/dev/'),
    re.compile(r'>\s*/boot/'),
    re.compile(r'>\s*/etc/'),
    # 任意代码执行
    re.compile(r'\beval\b'),
    # fork 炸弹
    re.compile(r':\(\)\s*\{.*:\|:&\s*;\s*\}'),
]


def _is_dangerous(command: str) -> bool:
    for pattern in _DANGEROUS_PATTERNS:
        if pattern.search(command):
            return True
    return False


@tool(
    name='execute_shell_command',
    description=(
        'Execute a shell command and return stdout/stderr/exit_code as JSON.\n\n'
        'Use your own judgment to assess if a command is dangerous '
        '(e.g. deleting files, modifying system config, remote script execution). '
        'If so, ask the user for permission before calling this tool.\n'
        'After the user explicitly confirms, call this tool with confirmed=True.'
    ),
    parameters={
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The shell command to execute, e.g. 'ls -l' or 'echo hello'"
            },
            "timeout": {
                "type": "integer",
                "description": "Maximum execution time in seconds (default: 30)"
            },
            "confirmed": {
                "type": "boolean",
                "description": "Set to true only if the user has explicitly confirmed they want this command to run despite it being flagged as potentially dangerous."
            },
        },
        "required": ["command", "confirmed"],
    },
)
def execute_shell_command(command, timeout=30, confirmed=False):
    if not command or not command.strip():
        return json.dumps({'stdout': '', 'stderr': 'Error: empty command.', 'exit_code': -1})

    if not confirmed and _is_dangerous(command):
        return json.dumps({
            'stdout': '',
            'stderr': (
                'This command has been flagged as potentially dangerous. '
                'Ask the user for explicit permission. '
                'If approved, call this tool again with confirmed=True; '
                'if denied, do not execute this command.'
            ),
            'exit_code': -1,
        })

    try:
        with Shell() as sh:
            result = sh.run(command, timeout=timeout)
            exit_code = result.exit_code()
            stdout_lines = list(result.stdout)
            stderr_lines = list(result.stderr)

        stdout = '\n'.join(stdout_lines)
        stderr = '\n'.join(stderr_lines)
        return json.dumps({
            'stdout': stdout,
            'stderr': stderr,
            'exit_code': exit_code,
        })
    except TimeoutError:
        return json.dumps({
            'stdout': '',
            'stderr': f'Error: command execution timed out ({timeout}s).',
            'exit_code': -1,
        })
    except Exception as e:
        return json.dumps({
            'stdout': '',
            'stderr': f'Error executing command: {e}',
            'exit_code': -1,
        })