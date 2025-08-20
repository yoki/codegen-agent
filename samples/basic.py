import pandas as pd
import asyncio

from codegen_agent.core.llm_client import create_client, LLMModels
from codegen_agent.core.models import CodeGenerationRequest
from codegen_agent.core.workflow import AgentWorkflow

tips = pd.read_csv("https://raw.githubusercontent.com/mwaskom/seaborn-data/master/tips.csv")

client = create_client(model=LLMModels.GEMINI25_FLASH)

request = CodeGenerationRequest(
    request_text="Calculate average tip percentage by day of week and time (lunch/dinner), create a pivot table, and visualize with a heatmap",
    user_variables={"tips_data": tips},
)
workflow = AgentWorkflow(request=request, client=client, max_code_generation=3)

# Generate code and refine until output is satisfactory
result = asyncio.run(workflow.run())
