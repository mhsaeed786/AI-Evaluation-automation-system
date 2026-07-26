"""
Sandbox — run generated code in isolated virtual environment.

Creates a temporary venv, installs deps, runs the code,
captures stdout/stderr. Never runs untrusted code in the main environment.
"""

import subprocess
import tempfile
import logging
import venv
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class Sandbox:
    """Execute generated code in an isolated venv."""

    def __init__(self, base_dir: Optional[str] = None):
        self._base = Path(base_dir) if base_dir else Path(tempfile.mkdtemp(prefix="oneagent_sandbox_"))

    def create_env(self, env_name: str = "test") -> Path:
        """Create an isolated virtual environment."""
        env_path = self._base / env_name
        if not env_path.exists():
            venv.create(str(env_path), with_pip=True, clear=True)
        return env_path

    def install_deps(self, env_path: Path, deps: List[str]) -> bool:
        """Install dependencies in the isolated env."""
        if not deps:
            return True
        pip = str(env_path / "Scripts" / "pip") if (env_path / "Scripts").exists() else str(env_path / "bin" / "pip")
        try:
            result = subprocess.run(
                [pip, "install", "-q"] + deps,
                capture_output=True, text=True, timeout=120,
            )
            if result.returncode != 0:
                logger.error(f"pip install failed: {result.stderr}")
                return False
            return True
        except subprocess.TimeoutExpired:
            logger.error("pip install timed out")
            return False

    def run_code(
        self,
        env_path: Path,
        code: str,
        timeout: int = 60,
        filename: str = "test_module.py",
    ) -> Tuple[bool, str, str]:
        """Run code in the isolated env, return (success, stdout, stderr)."""
        script = env_path / filename
        script.write_text(code, encoding="utf-8")
        python = str(env_path / "Scripts" / "python") if (env_path / "Scripts").exists() else str(env_path / "bin" / "python")
        try:
            result = subprocess.run(
                [python, str(script)],
                capture_output=True, text=True, timeout=timeout,
                cwd=str(env_path),
            )
            return result.returncode == 0, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return False, "", "Execution timed out"

    def run_tests(
        self,
        env_path: Path,
        test_code: str,
        module_code: str,
        timeout: int = 60,
    ) -> Tuple[bool, str]:
        """Run pytest in the isolated env."""
        # Write module and test
        (env_path / "module_under_test.py").write_text(module_code, encoding="utf-8")
        (env_path / "test_generated.py").write_text(test_code, encoding="utf-8")

        python = str(env_path / "Scripts" / "python") if (env_path / "Scripts").exists() else str(env_path / "bin" / "python")
        try:
            result = subprocess.run(
                [python, "-m", "pytest", "test_generated.py", "-v", "--tb=short"],
                capture_output=True, text=True, timeout=timeout,
                cwd=str(env_path),
            )
            output = result.stdout + "\n" + result.stderr
            return result.returncode == 0, output
        except subprocess.TimeoutExpired:
            return False, "Test execution timed out"

    def cleanup(self, env_name: Optional[str] = None):
        """Remove sandbox environments."""
        import shutil
        if env_name:
            path = self._base / env_name
            if path.exists():
                shutil.rmtree(path)
        elif self._base.exists():
            shutil.rmtree(self._base)


_sandbox: Optional[Sandbox] = None


def get_sandbox() -> Sandbox:
    global _sandbox
    if _sandbox is None:
        _sandbox = Sandbox()
    return _sandbox
