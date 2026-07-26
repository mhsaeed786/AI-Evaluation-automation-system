import os
import sys
import subprocess
import tempfile
import time
import json
import shutil
from typing import Dict, Any, Optional, Tuple


class SandboxEnvironment:
    """
    Isolated execution environment for running self-authored Python code
    and test suites inside isolated temporary directories or virtual environments.
    """

    def __init__(self, use_venv: bool = False, base_dir: Optional[str] = None):
        self.use_venv = use_venv
        self.base_dir = base_dir or tempfile.gettempdir()

    def _create_isolated_workspace(self) -> str:
        workspace = tempfile.mkdtemp(prefix="oneagent_sandbox_", dir=self.base_dir)
        return workspace

    def run_code_in_sandbox(
        self,
        code: str,
        entry_function: str = "process",
        sample_input: Optional[Dict[str, Any]] = None,
        timeout_sec: float = 5.0
    ) -> Dict[str, Any]:
        """
        Executes a Python code snippet inside an isolated sandbox subprocess.
        Passes JSON serialized sample_input to stdin or script wrapper and captures output.
        """
        workspace = self._create_isolated_workspace()
        sample_input = sample_input or {}

        try:
            module_path = os.path.join(workspace, "target_module.py")
            runner_path = os.path.join(workspace, "runner.py")

            with open(module_path, "w", encoding="utf-8") as f:
                f.write(code)

            runner_script = f"""import json
import sys
from target_module import *

def main():
    raw_input = sys.stdin.read()
    data = json.loads(raw_input) if raw_input.strip() else {{}}
    
    # Try calling the entry function or standard process function
    target_fn = globals().get("{entry_function}") or globals().get("process")
    if not target_fn:
        # Search for any function ending with _processor or process
        for k, v in globals().items():
            if callable(v) and (k.endswith("_processor") or k == "process"):
                target_fn = v
                break
                
    if not target_fn:
        raise AttributeError("No entry function '{entry_function}' or '_processor' function found in module")
        
    res = target_fn(data)
    print("---SANDBOX_RESULT_START---")
    print(json.dumps(res, indent=2, default=str))
    print("---SANDBOX_RESULT_END---")

if __name__ == "__main__":
    main()
"""
            with open(runner_path, "w", encoding="utf-8") as f:
                f.write(runner_script)

            start_time = time.time()
            proc = subprocess.Popen(
                [sys.executable, runner_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=workspace,
                text=True
            )

            input_str = json.dumps(sample_input)
            try:
                stdout, stderr = proc.communicate(input=input_str, timeout=timeout_sec)
                elapsed_ms = round((time.time() - start_time) * 1000, 2)

                if proc.returncode != 0:
                    return {
                        "success": False,
                        "output": None,
                        "error": f"Execution failed with return code {proc.returncode}: {stderr.strip()}",
                        "stdout": stdout,
                        "stderr": stderr,
                        "execution_time_ms": elapsed_ms
                    }

                # Extract sandbox result from marker
                if "---SANDBOX_RESULT_START---" in stdout and "---SANDBOX_RESULT_END---" in stdout:
                    json_chunk = stdout.split("---SANDBOX_RESULT_START---")[1].split("---SANDBOX_RESULT_END---")[0].strip()
                    parsed_result = json.loads(json_chunk)
                    return {
                        "success": True,
                        "output": parsed_result,
                        "error": None,
                        "stdout": stdout,
                        "stderr": stderr,
                        "execution_time_ms": elapsed_ms
                    }
                else:
                    return {
                        "success": True,
                        "output": stdout.strip(),
                        "error": None,
                        "stdout": stdout,
                        "stderr": stderr,
                        "execution_time_ms": elapsed_ms
                    }

            except subprocess.TimeoutExpired:
                proc.kill()
                return {
                    "success": False,
                    "output": None,
                    "error": f"Sandbox timeout expired after {timeout_sec} seconds",
                    "stdout": "",
                    "stderr": "Timeout expired",
                    "execution_time_ms": timeout_sec * 1000
                }

        finally:
            shutil.rmtree(workspace, ignore_errors=True)

    def run_tests_in_sandbox(
        self,
        module_code: str,
        test_code: str,
        module_slug: str = "module",
        timeout_sec: float = 10.0
    ) -> Dict[str, Any]:
        """
        Runs unit tests (via pytest or unittest) in an isolated sandbox workspace.
        """
        workspace = self._create_isolated_workspace()

        try:
            module_file = os.path.join(workspace, f"{module_slug}.py")
            test_file = os.path.join(workspace, f"test_{module_slug}.py")

            with open(module_file, "w", encoding="utf-8") as f:
                f.write(module_code)

            # Ensure test imports module correctly
            if f"import {module_slug}" not in test_code and f"from {module_slug}" not in test_code:
                header = f"import sys\nimport os\nsys.path.insert(0, os.path.dirname(__file__))\nfrom {module_slug} import *\n\n"
                test_code = header + test_code

            with open(test_file, "w", encoding="utf-8") as f:
                f.write(test_code)

            start_time = time.time()

            # Try running pytest if installed, else run unittest runner
            cmd = [sys.executable, "-m", "pytest", test_file, "-v", "--tb=short"]
            
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=workspace,
                text=True
            )

            try:
                stdout, stderr = proc.communicate(timeout=timeout_sec)
                elapsed_ms = round((time.time() - start_time) * 1000, 2)

                # Fallback to unittest if pytest module isn't available
                if "No module named pytest" in stderr or "No module named pytest" in stdout or proc.returncode != 0:
                    unittest_runner = f"""import unittest
import sys
import os
sys.path.insert(0, r'{workspace}')
import test_{module_slug}

suite = unittest.defaultTestLoader.loadTestsFromModule(test_{module_slug})
runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(suite)
passed = result.testsRun - len(result.failures) - len(result.errors)
failed = len(result.failures) + len(result.errors)
print(f"---TEST_RESULTS_START---")
print(f"passed: {{passed}}")
print(f"failed: {{failed}}")
print(f"total: {{result.testsRun}}")
print(f"---TEST_RESULTS_END---")
sys.exit(0 if result.wasSuccessful() else 1)
"""
                    unittest_file = os.path.join(workspace, "run_unittest.py")
                    with open(unittest_file, "w", encoding="utf-8") as f:
                        f.write(unittest_runner)

                    proc2 = subprocess.Popen(
                        [sys.executable, unittest_file],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        cwd=workspace,
                        text=True
                    )
                    stdout2, stderr2 = proc2.communicate(timeout=timeout_sec)
                    stdout = stdout2
                    stderr = stderr2
                    proc = proc2

                return {
                    "returncode": proc.returncode,
                    "stdout": stdout,
                    "stderr": stderr,
                    "elapsed_ms": elapsed_ms,
                    "workspace": workspace
                }

            except subprocess.TimeoutExpired:
                proc.kill()
                return {
                    "returncode": -1,
                    "stdout": "",
                    "stderr": f"Test runner timeout expired after {timeout_sec}s",
                    "elapsed_ms": timeout_sec * 1000,
                    "workspace": workspace
                }

        finally:
            shutil.rmtree(workspace, ignore_errors=True)
