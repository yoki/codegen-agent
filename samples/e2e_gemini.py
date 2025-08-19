# sample_e2e_gemini.py
# End-to-end: real Gemini → codegen → Docker execute → assessment (workflow loop)
# Requires: GEMINI_API_KEY (or GEMINI_API_KEY_FOR_DATA_AGENCY), Docker running, `pip install -e .`

from __future__ import annotations
import asyncio
import os
import pandas as pd

from codegen_agent.core.clients.llm import create_client, LLMModels
from codegen_agent.core.models import CodeGenerationRequest
from codegen_agent.core.llm_service import CodeGenerationService, AssessmentService
from codegen_agent.core.workflow.agent_workflow import AgentWorkflow


async def main() -> int:
    if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY_FOR_DATA_AGENCY")):
        raise SystemExit("Set GEMINI_API_KEY (or GEMINI_API_KEY_FOR_DATA_AGENCY)")

    client = create_client(LLMModels.GEMINI25_FLASH)

    # Real data variable passed to AI
    df = pd.DataFrame({"country": ["SG", "US", "JP"], "gdp": [500, 23000, 5100]})
    variables = {"df": df}

    # Simple, deterministic request so stdout can be validated by-eye
    req_text = (
        "Using df, print exactly two lines: "
        "'rows=<N>' where N is len(df), and 'avg_gdp=<X>' where X is the mean of gdp rounded to 2 decimals. "
        "Use only pandas/numpy/matplotlib/seaborn."
    )

    request = CodeGenerationRequest(request_text=req_text, user_variables=variables)
    workflow = AgentWorkflow(
        request=request,
        codegen=CodeGenerationService(client),
        assessor=AssessmentService(client),
        ui=None,
        max_code_generation=3,
    )

    await workflow.run()
    print("[OK] sample_e2e_gemini finished")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
