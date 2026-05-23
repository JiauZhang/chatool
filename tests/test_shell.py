from conippets import json
from chatool.tools.shell import execute_shell_command


class TestExecuteShellCommand:
    def test_echo(self):
        result = json.loads(execute_shell_command(command="echo hello", confirmed=True))
        assert result["exit_code"] == 0
        assert "hello" in result["stdout"]

    def test_exit_code_non_zero(self):
        result = json.loads(
            execute_shell_command(command="python3 -c 'exit(42)'", confirmed=True)
        )
        assert result["exit_code"] == 42

    def test_stderr_captured(self):
        result = json.loads(
            execute_shell_command(
                command="python3 -c 'import sys; sys.stderr.write(\"err msg\")'",
                confirmed=True,
            )
        )
        assert "err msg" in result["stderr"]

    def test_empty_command(self):
        result = json.loads(execute_shell_command(command="", confirmed=False))
        assert result["exit_code"] == -1
        assert "empty" in result["stderr"].lower()

    def test_dangerous_command_blocked_without_confirmation(self):
        result = json.loads(
            execute_shell_command(command="rm -rf /tmp/foo", confirmed=False)
        )
        assert result["exit_code"] == -1
        assert "dangerous" in result["stderr"].lower()

    def test_safe_command_without_confirmation_allowed(self):
        """confirmed=False only blocks dangerous commands, safe ones should pass."""
        result = json.loads(
            execute_shell_command(command="echo safe", confirmed=False)
        )
        assert result["exit_code"] == 0
        assert "safe" in result["stdout"]


class TestTimeout:
    def test_timeout(self):
        result = json.loads(
            execute_shell_command(command="sleep 10", timeout=1, confirmed=True)
        )
        assert result["exit_code"] == -1
        assert "timed out" in result["stderr"].lower()
