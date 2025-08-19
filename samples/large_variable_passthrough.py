# sample_large_variable_passthrough.py
# Direct Docker execution (no LLM). Sends a ~50k-row DataFrame into the container and computes stats.
# Validates pickle marshalling and performance of mounts.

from __future__ import annotations
import pandas as pd
import numpy as np
from codegen_agent.core.execution.runner import execute


def make_df(n: int = 50_000) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    return pd.DataFrame(
        {
            "id": np.arange(n),
            "value": rng.normal(0, 1, size=n),
        }
    )


CODE = r"""
import sys
import numpy as np

n = len(df)
m = float(np.mean(df["value"]))
print(f"OK: rows={n}, mean≈{m:.4f}")
"""

if __name__ == "__main__":
    variables = {"df": make_df()}
    res = execute(CODE, variables)
    print("\n---- STDOUT ----\n", res.stdout)
    if res.stderr.strip():
        print("\n---- STDERR ----\n", res.stderr)
    print("\nReturn code:", res.returncode)
