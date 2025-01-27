from langgraph.graph import StateGraph, END
from agents import AgentState
from agents import agent_preprocessor, agent_code_generation, agent_extract_code, agent_code_review, agent_execute_code_in_docker, agent_concise_llm_output 
from agents import conditional_should_continue_after_extraction, conditional_should_continue_after_code_review, conditional_should_continue_after_docker_run

# Create a StateGraph to model the workflow
workflow = StateGraph(AgentState)

# Add nodes for each step
workflow.add_node("agent_preprocessor", agent_preprocessor)
workflow.add_node("agent_code_generation", agent_code_generation)
workflow.add_node("agent_extract_code", agent_extract_code)
workflow.add_node("agent_code_review", agent_code_review)
workflow.add_node("agent_execute_code_in_docker", agent_execute_code_in_docker)
workflow.add_node("agent_concise_llm_output", agent_concise_llm_output)

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

workflow.add_conditional_edges(
    "agent_execute_code_in_docker",
    conditional_should_continue_after_docker_run,
    {
        "continue": "agent_concise_llm_output",
        "regenerate": "agent_code_generation"
    }
)

workflow.add_edge("agent_concise_llm_output", END)

# Compile the workflow
app = workflow.compile()

# #helper method to visualize graph
# def save_graph_to_file(runnable_graph, output_file_path):
#     png_bytes = runnable_graph.get_graph().draw_mermaid_png()
#     with open(output_file_path, 'wb') as file:
#         file.write(png_bytes)

# save_graph_to_file(app, "output.png")