# sample_codegen_then_exec.py
# Real Gemini codegen → explicit Docker execution (no workflow orchestration)
# Requires: GEMINI_API_KEY (or GEMINI_API_KEY_FOR_DATA_AGENCY), Docker running

from __future__ import annotations
import asyncio
import os
import pandas as pd

from codegen_agent.core.llm_client import create_client, LLMModels
from codegen_agent.core.models import CodeGenerationRequest
from codegen_agent.core.llm_service import CodeGenerationService
from codegen_agent.core.execution.runner import execute


async def main() -> int:
    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY_FOR_DATA_AGENCY")):
        raise SystemExit("Set GEMINI_API_KEY (or GEMINI_API_KEY_FOR_DATA_AGENCY)")

    client = create_client(LLMModels.GEMINI25_FLASH)

    # Variables to pass
    s = pd.Series([10, 20, 30, 40], name="x")
    variables = {"s": s}

    # Ask Gemini to generate code that uses `s` and prints summary stats
    req_text = (
        "Given pandas Series s, print one line 'sum=<S>, mean=<M>, count=<C>' "
        "with integers where appropriate and mean rounded to 1 decimal. "
        "Use only pandas/numpy/matplotlib/seaborn."
    )
    request = CodeGenerationRequest(request_text=req_text, user_variables=variables)

    code = (await CodeGenerationService(client).generate_code(request)).code
    print("---- Generated code ----\n", code, "\n------------------------")

    result = execute(code, variables)
    print("\n---- Docker STDOUT ----\n", result.stdout)
    if result.stderr.strip():
        print("\n---- Docker STDERR ----\n", result.stderr)
    print("\nReturn code:", result.returncode)

    return 0 if result.returncode == 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
