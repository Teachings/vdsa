from langgraph.graph import StateGraph, END
from agents import AgentState
from agents import agent_preprocessor, agent_code_generation, agent_extract_code, agent_code_review, agent_execute_code_in_docker 
from agents import conditional_should_continue_after_extraction, conditional_should_continue_after_code_review

# Create a StateGraph to model the workflow
workflow = StateGraph(AgentState)

# Add nodes for each step
workflow.add_node("agent_preprocessor", agent_preprocessor)
workflow.add_node("agent_code_generation", agent_code_generation)
workflow.add_node("agent_extract_code", agent_extract_code)
workflow.add_node("agent_code_review", agent_code_review)
workflow.add_node("agent_execute_code_in_docker", agent_execute_code_in_docker)

# Set entry point
workflow.set_entry_point("agent_preprocessor")

# Define edges
workflow.add_edge("agent_preprocessor", "agent_code_generation")
workflow.add_edge("agent_code_generation", "agent_extract_code")

workflow.add_conditional_edges(
    "agent_extract_code",
    conditional_should_continue_after_extraction,
    {
        "continue": "agent_code_review",
        "regenerate": "agent_code_generation"
    }
)

workflow.add_conditional_edges(
    "agent_code_review",
    conditional_should_continue_after_code_review,
    {
        "continue": "agent_execute_code_in_docker",
        "regenerate": "agent_code_generation"
    }
)

workflow.add_edge("agent_execute_code_in_docker", END)

# Compile the workflow
app = workflow.compile()
