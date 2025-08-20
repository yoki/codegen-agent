from __future__ import annotations
import asyncio
import nest_asyncio
from IPython.display import Markdown, display
from IPython.core.getipython import get_ipython

from ..core.models import CodeGenerationRequest
from ..core.workflow import AgentWorkflow
from ..core.llm_service import CodeGenerationService, AssessmentService
from .display import DisplayService


class NotebookAgent:
    def __init__(self, client):
        self.client = client
        self.MAX_CODE_GENERATION = 3

    async def run(self, line: str, cell: str = ""):
        if not cell:
            display(Markdown("Please provide a request for analysis in the second line."))
            return
        user_vars = self._collect_user_vars(line)
        display(Markdown("Starting to generate code for you..."))
        req = CodeGenerationRequest(request_text=cell, user_variables=user_vars)

        ui = DisplayService()
        wf = AgentWorkflow(
            request=req,
            client=self.client,
            ui=ui,
            max_code_generation=self.MAX_CODE_GENERATION,
        )
        await wf.run()

    def _collect_user_vars(self, line: str):
        ip = get_ipython()
        ns = getattr(ip, "user_ns", {}) if ip else {}
        names = line.strip().split()
        out = {}
        for n in names:
            if n in ns:
                v = ns[n]
                if isinstance(v, dict):
                    for k, vv in v.items():
                        out[f"{n}_{k}"] = vv
                else:
                    out[n] = v
        return out


def analyze(line="", cell="", *, client=None):
    nest_asyncio.apply()
    if client is None:
        raise RuntimeError("Please pass an LLM client via analyze(..., client=...) ")
    agent = NotebookAgent(client)
    return asyncio.run(agent.run(line, cell))
