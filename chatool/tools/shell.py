import subprocess
from chatchat.tool import tool

@tool(
    name='execute_shell_command',
    description='执行一条 shell 命令并返回其标准输出和标准错误。注意：该命令会直接在系统上运行，请避免使用危险操作。',
    parameters={
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "要执行的 shell 命令，例如 'ls -l' 或 'echo hello'"
            }
        },
        "required": ["command"],
    },
)
def execute_shell_command(command):
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=30,
        )
        output = result.stdout
        if result.stderr:
            output += "\n[STDERR]\n" + result.stderr
        if not output.strip():
            output = "(无输出)"
        return output.strip()
    except subprocess.TimeoutExpired:
        return f"错误：命令执行超过30秒超时。"
    except Exception as e:
        return f"执行命令时发生异常：{str(e)}"
