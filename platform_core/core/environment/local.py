import os
import subprocess
from typing import List
from platform_core.core.environment.base import Environment

class LocalEnvironment(Environment):
    def __init__(self, workspace_path: str):
        self.workspace_path = os.path.abspath(workspace_path)
        os.makedirs(self.workspace_path, exist_ok=True)

    def _get_absolute_path(self, path: str) -> str:
        """Resolve a path to an absolute path and enforce that it is within the workspace_path."""
        # Convert path to absolute
        if os.path.isabs(path):
            abs_path = os.path.abspath(path)
        else:
            abs_path = os.path.abspath(os.path.join(self.workspace_path, path))
            
        # Enforce sandbox: check if resolved path starts with the workspace path
        try:
            common = os.path.commonpath([self.workspace_path, abs_path])
            if common != self.workspace_path:
                raise PermissionError(
                    f"Access Denied: Path '{path}' resolves outside the allowed workspace '{self.workspace_path}'."
                )
        except ValueError:
            raise PermissionError(
                f"Access Denied: Path '{path}' is on a different drive or invalid."
            )
            
        return abs_path

    def read_file(self, path: str) -> str:
        abs_path = self._get_absolute_path(path)
        with open(abs_path, 'r', encoding='utf-8') as f:
            return f.read()

    def write_file(self, path: str, content: str) -> None:
        abs_path = self._get_absolute_path(path)
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, 'w', encoding='utf-8') as f:
            f.write(content)

    def exists(self, path: str) -> bool:
        try:
            abs_path = self._get_absolute_path(path)
            return os.path.exists(abs_path)
        except PermissionError:
            return False

    def run_command(self, command: List[str] | str, cwd: str = None) -> str:
        from platform_core.core.environment.base import CommandExecutionError
        # Determine working directory within sandbox
        run_cwd = self.workspace_path
        if cwd:
            run_cwd = self._get_absolute_path(cwd)
            
        # Execute command safely
        shell = isinstance(command, str)
        result = subprocess.run(
            command,
            cwd=run_cwd,
            text=True,
            capture_output=True,
            shell=shell
        )
        if result.returncode != 0:
            raise CommandExecutionError(command, result.returncode, result.stdout, result.stderr)
        return result.stdout

    def list_dir(self, path: str) -> List[str]:
        abs_path = self._get_absolute_path(path)
        if not os.path.isdir(abs_path):
            return []
        return os.listdir(abs_path)

    def delete_file(self, path: str) -> None:
        abs_path = self._get_absolute_path(path)
        if os.path.isfile(abs_path):
            os.remove(abs_path)
        elif os.path.isdir(abs_path):
            import shutil
            shutil.rmtree(abs_path)
