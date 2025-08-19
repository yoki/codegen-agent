from __future__ import annotations
from typing import List, Optional, Dict, Any

from .models import (
    CodeGenerationRequest,
    CodeGenerationResult,
    ExecutionResult,
    CodeAssessmentResult,
    ExecutionAssessmentHistoryItem,
)
from .llm_service import CodeGenerationService, AssessmentService
from .execution.runner import execute as sandbox_execute
from typing import Protocol, Optional


class UI(Protocol):
    def show_generated_code(
        self, code: str, explanation: Optional[str] = None, trial_number: Optional[int] = None
    ): ...
    def show_results(self, execution_result: ExecutionResult, trial_number: Optional[int] = None): ...
    def show_assessment(self, assessment: CodeAssessmentResult): ...
    def save_to_notebook(self, request: CodeGenerationRequest, code: str): ...
    def clean_code_section(self): ...


class NullUI:
    def show_generated_code(self, code: str, explanation: Optional[str] = None, trial_number: Optional[int] = None):
        pass

    def show_results(self, execution_result: ExecutionResult, trial_number: Optional[int] = None):
        pass

    def show_assessment(self, assessment: CodeAssessmentResult):
        pass

    def save_to_notebook(self, request: CodeGenerationRequest, code: str):
        pass

    def clean_code_section(self):
        pass


class AgentWorkflow:
    """Straightforward generate→execute→assess loop, no external state machine dependency."""

    def __init__(
        self,
        request: CodeGenerationRequest,
        *,
        codegen: CodeGenerationService,
        assessor: AssessmentService,
        ui: UI = NullUI(),
        max_code_generation: int = 3,
    ):
        self.request = request
        self.codegen = codegen
        self.assessor = assessor
        self.ui = ui
        self.max_code_generation = max_code_generation
        self.code_generation_count = 0

        self.current_code: str = ""
        self.code_result: CodeGenerationResult = CodeGenerationResult.empty_result()
        self.execution_result: ExecutionResult = ExecutionResult.empty_result()
        self.assessment: CodeAssessmentResult = CodeAssessmentResult.empty_assessment()
        self.history: List[ExecutionAssessmentHistoryItem] = []

    async def run(self) -> None:
        # First generation
        self.code_result = await self.codegen.generate_code(self.request)
        self.current_code = self.code_result.code
        self.ui.show_generated_code(self.current_code, trial_number=self.code_generation_count + 1)

        while True:
            # Execute
            self.execution_result = sandbox_execute(self.current_code, self.request.user_variables)
            self.ui.show_results(self.execution_result, trial_number=self.code_generation_count + 1)

            # Assess
            self.code_generation_count += 1
            orig_plan = self.assessment.plan
            self.assessment = await self.assessor.assess_code_output(
                self.request, self.execution_result, self.current_code, self.history
            )
            self.ui.show_assessment(self.assessment)

            self.history.append(
                ExecutionAssessmentHistoryItem(
                    plan=orig_plan,
                    code=self.current_code,
                    execution_result=self.execution_result,
                    assessment=self.assessment,
                )
            )

            if self.assessment.success:
                self.ui.save_to_notebook(self.request, self.current_code)
                self.ui.clean_code_section()
                return

            if self.code_generation_count >= self.max_code_generation:
                return

            if self.assessment.should_retry and self.assessment.code:
                self.current_code = self.assessment.code
                continue

                # If should_retry is False or no code provided, stop.
