# sample_workflow_failed_then_recover.py
# Full workflow demo with an intentional failed assessment, then a corrected retry.
# - Uses a stateful fake LLM client ONLY to control LLM responses deterministically.
# - Executes code in your real Docker sandbox (no mocking of execution).
# - Shows the workflow loop: generate -> execute -> assess (fail) -> regenerate -> execute -> assess (succeed).

from __future__ import annotations
import asyncio
import json
from types import SimpleNamespace

from codegen_agent.core.models import (
    CodeGenerationRequest,
    CodeGenerationResult,
    CodeAssessmentResult,
    ExecutionResult,
    ExecutionAssessmentHistoryItem,
)
from codegen_agent.core.llm_service import CodeGenerationService, AssessmentService
from codegen_agent.core.workflow.agent_workflow import AgentWorkflow


# ----------------------------
# Fake LLM: deterministic behavior
# ----------------------------
class DeterministicLLM:
    """
    Returns:
      - First call for CodeGenerationResult: code that prints 'hello' (lowercase).
      - First call for CodeAssessmentResult: mark failure, request retry with corrected code (prints 'HELLO').
      - Second call for CodeAssessmentResult: mark success (no retry).
    """

    def __init__(self):
        self.codegen_calls = 0
        self.assess_calls = 0

    async def create(self, *, messages, json_output):
        if json_output is CodeGenerationResult:
            self.codegen_calls += 1
            # Intentional "wrong" code: prints lowercase 'hello'
            payload = {"code": "print('hello')"}
            return SimpleNamespace(content=json.dumps(payload))

        if json_output is CodeAssessmentResult:
            self.assess_calls += 1
            if self.assess_calls == 1:
                # First assessment: fail because stdout will be 'hello', not 'HELLO'
                payload = {
                    "analysis": "Expected 'HELLO' but saw lowercase. Correct casing.",
                    "success": False,
                    "should_retry": True,
                    "plan": "Regenerate code to print 'HELLO' exactly.",
                    "code": "print('HELLO')",
                }
            else:
                # Second assessment: success
                payload = {
                    "analysis": "Output matches exactly.",
                    "success": True,
                    "should_retry": False,
                    "plan": "",
                    "code": "",
                }
            return SimpleNamespace(content=json.dumps(payload))

        # Fallback (shouldn't happen here)
        return SimpleNamespace(content=json.dumps({}))


# ----------------------------
# Minimal UI (no IPython)
# ----------------------------
class PrintUI:
    def show_generated_code(self, code: str, explanation=None, trial_number=None):
        tag = f"(Attempt {trial_number})" if trial_number else ""
        print("\n=== Generated Code", tag, "===\n", code, sep="")

    def show_results(self, execution_result: ExecutionResult, trial_number=None):
        tag = f"(Attempt {trial_number})" if trial_number else ""
        print("\n=== Execution Results", tag, "===\nSTDOUT:\n", execution_result.stdout, sep="")
        if execution_result.stderr.strip():
            print("STDERR:\n", execution_result.stderr, sep="")

    def show_assessment(self, assessment: CodeAssessmentResult):
        print("\n=== Assessment ===")
        print("Success:", assessment.success)
        print("Should Retry:", assessment.should_retry)
        if assessment.analysis:
            print("Analysis:", assessment.analysis)
        if assessment.plan:
            print("Plan:", assessment.plan)

    def save_to_notebook(self, request: CodeGenerationRequest, code: str):
        print("\n[Saved] Final code prepared for notebook/cell:\n", code, sep="")

    def clean_code_section(self):
        pass


# ----------------------------
# Main: run the workflow
# ----------------------------
async def main() -> int:
    # User request that demands exact uppercase 'HELLO'
    request = CodeGenerationRequest(
        request_text="Print exactly HELLO (uppercase). Use only allowed libraries.",
        user_variables={},  # No variables needed
    )

    client = DeterministicLLM()
    ui = PrintUI()

    wf = AgentWorkflow(
        request=request,
        codegen=CodeGenerationService(client),
        assessor=AssessmentService(client),
        ui=ui,
        max_code_generation=3,
    )

    await wf.run()
    print("\n[OK] Workflow finished (expected: 1st assessment fails, 2nd succeeds).")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
