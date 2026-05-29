import abc
from typing import List

class CommandExecutionError(RuntimeError):
    def __init__(self, command: List[str] | str, returncode: int, stdout: str, stderr: str):
        self.command = command
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        msg = f"Command {command} failed with exit code {returncode}.\nStderr: {stderr}\nStdout: {stdout}"
        super().__init__(msg)

class Environment(abc.ABC):
    @abc.abstractmethod
    def read_file(self, path: str) -> str:
        """Read text content from a file."""
        pass

    @abc.abstractmethod
    def write_file(self, path: str, content: str) -> None:
        """Write text content to a file."""
        pass

    @abc.abstractmethod
    def exists(self, path: str) -> bool:
        """Check if a file or directory exists."""
        pass

    @abc.abstractmethod
    def run_command(self, command: List[str] | str, cwd: str = None) -> str:
        """Run a CLI command in the environment and return stdout output.
        Raises CommandExecutionError if the exit code is non-zero.
        """
        pass

    @abc.abstractmethod
    def list_dir(self, path: str) -> List[str]:
        """List files and subdirectories in a directory."""
        pass

    @abc.abstractmethod
    def delete_file(self, path: str) -> None:
        """Delete a file in the environment."""
        pass
