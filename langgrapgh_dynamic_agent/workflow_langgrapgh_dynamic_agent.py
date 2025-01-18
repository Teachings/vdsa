from langgraph.graph import StateGraph, END
from termcolor import colored

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

# Add edges between nodes
workflow.add_edge("agent_preprocessor", "agent_code_generation")
workflow.add_edge("agent_code_generation", "agent_extract_code")

# Add conditional edges 
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

# Compile and run the workflow with debug messages
app = workflow.compile()

#helper method to visualize graph
def save_graph_to_file(runnable_graph, output_file_path):
    png_bytes = runnable_graph.get_graph().draw_mermaid_png()
    with open(output_file_path, 'wb') as file:
        file.write(png_bytes)

save_graph_to_file(app, "output.png")


# List of initial requests
initial_requests = [
    "How many r are in strawberry?"
]

# Iterate over each request
for request in initial_requests:
    initial_state = {
        "initial_request": request,
        "preprocessor_agent_result": "",
        "generated_code_result": "",
        "extracted_python_code": "",
        "code_review_result": "",
        "final_output": ""
    }

    try:
        # Run the workflow and observe the debug outputs
        result = app.invoke(initial_state)
        print(colored("", "white"))  # Adding a newline with white color for separation
        print(colored("FINAL Result:", "magenta"), colored(result["final_output"], "light_yellow"))
    
    except Exception as e:
        # Catch and log the error, then continue with the next request
        print(colored(f"ERROR: Failed to process request: '{request}'", "red"))
        print(colored(f"ERROR DETAILS: {str(e)}", "red"))
    
    # Pause for user input before moving to the next request
    input(colored("\nPress Enter to continue to the next request...\n", "yellow"))

