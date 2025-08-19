import os
import re
import shutil
import tempfile
import pickle
from pathlib import Path
from typing import Dict, Any, Set

# Optional pandas for DataFrame-friendly pickling
import pandas as pd


from ..models import ExecutionResult
from .docker_runtime import DockerRuntime
from .prelude import run as _PRELUDE_RUN  # only to access source file path


def _write_prelude_to(path: Path) -> None:
    # Find our installed prelude.py file content and copy under inputs
    prelude_src = Path(__file__).with_name("prelude.py")
    shutil.copyfile(prelude_src, path)


def _find_used_variables(code: str, namespace: Dict[str, Any]) -> Dict[str, Any]:
    # Very simple identifier scan; mirrors your earlier heuristic
    variable_pattern = r"\b([a-zA-Z_][a-zA-Z0-9_]*)\b"
    used: Set[str] = set(re.findall(variable_pattern, code))
    return {k: v for k, v in namespace.items() if k in used}


def _save_var(path: Path, value: Any) -> None:
    if pd is not None and hasattr(pd, "DataFrame") and isinstance(value, getattr(pd, "DataFrame")):
        value.to_pickle(path)  # type: ignore[attr-defined]
        return
    # generic pickle
    with open(path, "wb") as f:
        pickle.dump(value, f, protocol=pickle.HIGHEST_PROTOCOL)


def execute(code: str, variables: Dict[str, Any], *, image: str = "codegen-agent-runner:py313") -> ExecutionResult:
    """Execute code inside a disposable Docker container with RO inputs and RW outputs.

    Returns ExecutionResult(stdout, stderr, returncode).
    """
    tmp_root = Path(tempfile.mkdtemp(prefix="codegen_agent_"))
    inputs = tmp_root / "inputs"
    outputs = tmp_root / "outputs"
    vars_dir = inputs / "vars"

    try:
        inputs.mkdir(parents=True, exist_ok=True)
        outputs.mkdir(parents=True, exist_ok=True)
        vars_dir.mkdir(parents=True, exist_ok=True)

        # Write code
        (inputs / "code.py").write_text(code, encoding="utf-8")
        # Write prelude
        _write_prelude_to(inputs / "prelude.py")

        # Filter and serialize used variables
        filtered = _find_used_variables(code, variables)
        for name, val in filtered.items():
            _save_var(vars_dir / f"{name}.pkl", val)

        # Run container
        rt = DockerRuntime(image=image)
        rt.ensure_image()
        proc = rt.run(str(inputs), str(outputs))

        return ExecutionResult(stdout=proc.stdout, stderr=proc.stderr, returncode=proc.returncode)
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)
