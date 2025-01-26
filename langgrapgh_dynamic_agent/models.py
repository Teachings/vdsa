from typing import TypedDict
from pydantic import BaseModel, Field

class AgentDecision(BaseModel):
    timestamp: str
    user: str
    initial_request: str
    preprocessor_agent_result: str
    extracted_python_code: str
    final_output: str
    concise_llm_output: str

class CodeReviewResult(BaseModel):
    result: str = Field(..., description="The result of the code review: 'correct' or 'incorrect'.")
    message: str = Field(..., description="Optional message returned by the review agent.")

class ConciseLLMOutput(BaseModel):
    message: str = Field(..., description="response returned by LLM")

# Define the state
class AgentState(TypedDict):
    initial_request: str
    preprocessor_agent_result: str
    generated_code_result: str
    code_extraction_status: str
    extracted_python_code: str
    code_review_result: CodeReviewResult
    code_review_status: str
    final_output: str
    concise_llm_output: str