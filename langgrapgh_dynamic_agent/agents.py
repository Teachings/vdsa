from termcolor import colored
import re
import docker
import tempfile
import os
from pydantic import ValidationError
from langchain_ollama import ChatOllama
from models import CodeReviewResult, AgentState, ConciseLLMOutput
from utils import pretty_print_state_enhanced
from helpers import load_config


# Import the prompt templates from the new file
from prompts import preprocessor_prompt_template, code_generation_prompt_template, code_review_prompt_template, concise_llm_prompt_template
config = load_config()

log_level = config["log_level"]

# Define model
model = ChatOllama(
    base_url="http://localhost:11434",
    model=config["llm"]["preprocessor_model"] #deepseek-coder-v2 nemotron qwen2.5-coder:32b llama3.2
)

model_code_generator = ChatOllama(
    base_url="http://localhost:11434",
    model=config["llm"]["code_generator_model"] #deepseek-coder-v2 nemotron qwen2.5-coder:32b llama3.2
)

# Define model
model_json = ChatOllama(
    base_url="http://localhost:11434",
    model=config["llm"]["code_review_model"],
    format="json"
)
# config.get("device", "cuda")
# Initialize models for preprocessor, code generation, and code review agents
preprocessor_model = model
code_generator_model = model_code_generator
code_review_model = model_json.with_structured_output(CodeReviewResult)
concise_output_model = model_json.with_structured_output(ConciseLLMOutput)

# Initialize chains for preprocessor, code generation, and code review agents
preprocessor_agent_generator = preprocessor_prompt_template | preprocessor_model
agent_code_generator = code_generation_prompt_template | code_generator_model
code_review_agent_generator = code_review_prompt_template | code_review_model
concise_output_agent_generator = concise_llm_prompt_template | concise_output_model

def agent_preprocessor(state: AgentState):
    print(colored("Preprocessor: Architecting solution to the problem.", "magenta"))
    result = preprocessor_agent_generator.invoke({"user_request": state["initial_request"]})
    # print(colored(f"DEBUG: Preprocessor Result: {result.content}", "magenta"))
    state["preprocessor_agent_result"] = result.content
    if(log_level=="debug"):
        print(colored("DEBUG: agent_preprocessor state", "magenta"))
        pretty_print_state_enhanced(state)
    return state

def agent_code_generation(state: AgentState):
    print(colored("Generating code to solve the request.", "magenta"))
    
    # Check and reset the state at the beginning of the method if needed
    if (state["generated_code_result"] == "regenerate" or 
        state["code_review_result"] == "regenerate"):
        if(log_level=="debug"):
            print(colored("DEBUG: Resetting agent state due to regenerate flag...", "yellow"))
        reset_keys = [
            "generated_code_result", 
            "extracted_python_code", 
            "code_review_result", 
            "final_output"
        ]
        for key in reset_keys:
            state[key] = ""
    else:
        if(log_level=="debug"):
            print(colored("DEBUG: Initial Generation of code. No need to reset agent state.", "green"))
    
    # Continue with the rest of your code generation logic...
    result = agent_code_generator.invoke({"task": state["preprocessor_agent_result"]})
    # print(colored(f"DEBUG: Code Generation Result: {result.content}", "blue"))
    state["generated_code_result"] = result.content
    
    # Continue with the rest of your code generation logic...
    if(log_level=="debug"):
        print(colored("DEBUG: agent_code_generation state", "magenta"))
        pretty_print_state_enhanced(state)
    return state

def agent_extract_code(state: AgentState):
    if(log_level=="debug"):
        print(colored("Extracting Python Code...", "magenta"))
    # print(colored(f"DEBUG: Generated Code Result: {state['generated_code_result']}", "green"))
    code_result = state["generated_code_result"]
    code_block = re.search(r"```(?!python)(.*?)```", code_result, re.DOTALL)
    code_block_with_lang = re.search(r"```python(.*?)```", code_result, re.DOTALL)
    single_backtick_code = re.search(r"`(.*?)`", code_result, re.DOTALL)
    
    # 1. Try to extract code from triple backticks without the word 'python'
    if code_block:
        extracted_code = code_block.group(1).strip()
        state["extracted_python_code"] = extracted_code
        # print(colored(f"DEBUG: Extracted Python Code from triple backticks: {state['extracted_python_code']}", "green"))
        if(log_level=="debug"):
            print(colored("DEBUG: Extracted Python Code from triple backticks", "green"))
        state["code_extraction_status"] = "continue"
    
    # 2. If that fails, try to extract from triple backticks with 'python'
    elif code_block_with_lang:
        extracted_code = code_block_with_lang.group(1).strip()
        state["extracted_python_code"] = extracted_code
        # print(colored(f"DEBUG: Extracted Python Code from triple backticks with 'python': {state['extracted_python_code']}", "green"))
        if(log_level=="debug"):
            print(colored("DEBUG: Extracted Python Code from triple backticks with 'python'", "green"))
    
        state["code_extraction_status"] = "continue"
    
    # 3. If that fails, try to extract from single backticks
    elif single_backtick_code:
        extracted_code = single_backtick_code.group(1).strip()
        state["extracted_python_code"] = extracted_code
        # print(colored(f"DEBUG: Extracted Python Code from single backticks: {state['extracted_python_code']}", "green"))
        if(log_level=="debug"):
            print(colored("DEBUG: Extracted Python Code from single backtick", "green"))
        state["code_extraction_status"] = "continue"
    
    # 4. Fallback: Assume the entire result is the code if no backticks are found
    elif code_result:
        if(log_level=="debug"):
            print(colored("DEBUG: No backticks found. Assuming entire result is the code.", "yellow"))
            # print(colored(f"DEBUG: Fallback Extracted Python Code: {state['extracted_python_code']}", "yellow"))
        state["extracted_python_code"] = code_result.strip()
        state["code_extraction_status"] = "continue"
    else:
        state["code_extraction_status"] = "regenerate"  # Extraction failed, regenerate
    
    if(log_level=="debug"):
        print(colored("DEBUG: agent_extract_code state", "magenta"))
        pretty_print_state_enhanced(state)

    return state  # Always return state

def conditional_should_continue_after_extraction(state: AgentState):
    # Check if the extraction was successful and we have some code to work with
    if state["code_extraction_status"] == "continue":
        return "continue"
    else:
        return "regenerate"

def agent_code_review(state: AgentState):
    print(colored("Code Review: Ensuring everything is correct!", "magenta"))
    
    code_review_result = code_review_agent_generator.invoke({"generated_code": state["extracted_python_code"], "initial_request": state["preprocessor_agent_result"]})

    try:
        
        # Print and store in agent state
        # print(colored("Reviewed Code:", "yellow"))
        if isinstance(code_review_result, CodeReviewResult):
            # print(f"Result: {code_review_result.result}")
            # print(f"Message: {code_review_result.message}")
            state["code_review_result"] = code_review_result
        else:
            print(colored("Unexpected response format from code review agent.", "red"))

        # Update the review status based on the result
        if code_review_result.result == "correct":
            state["code_review_status"] = "continue"
        else:
            state["code_review_status"] = "regenerate"

    except ValidationError as e:
        print(colored(f"ERROR: Code review validation failed with error: {e}", "red"))
        state["code_review_status"] = "regenerate"
    
    except Exception as e:
        print(colored(f"ERROR: Error parsing JSON: {e}", "red"))
        state["code_review_status"] = "regenerate"

    if(log_level=="debug"):
        print(colored("DEBUG: agent_code_review state", "magenta"))
        pretty_print_state_enhanced(state)

    return state  # Always return state

def conditional_should_continue_after_code_review(state: AgentState):
    # Check if the extraction was successful and we have some code to work with
    if state["code_review_status"] == "continue":
        return "continue"
    else:
        return "regenerate"

def agent_execute_code_in_docker(state: AgentState):
    print(colored("Containerized Execution: Safely executing code in docker container.", "magenta"))
    
    with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as temp_code_file:
        temp_code_file.write(state["extracted_python_code"].encode('utf-8'))
        temp_code_filename = temp_code_file.name

    client = docker.from_env()
    try:
        container_output = client.containers.run(
            image="python:3.9-slim",
            command=f"python {os.path.basename(temp_code_filename)}",
            volumes={os.path.dirname(temp_code_filename): {'bind': '/usr/src/app', 'mode': 'rw'}},
            working_dir="/usr/src/app",
            remove=True,
            stdout=True,
            stderr=True
        )
        # Clean output: remove whitespace and ensure string type
        state["final_output"] = container_output.decode('utf-8').strip()  # Strip newlines
    except docker.errors.ContainerError as e:
        print(colored(f"ERROR: Error running code in container: {str(e)}", "red"))
        state["final_output"] = ""  # Ensure fallback value is string
    
    os.remove(temp_code_filename)

    if(log_level=="debug"):
        print(colored("DEBUG: agent_execute_code_in_docker state", "magenta"))
        pretty_print_state_enhanced(state)
    return state

def conditional_should_continue_after_docker_run(state: AgentState):
    # Return "regenerate" if final_output is None or an empty string; otherwise, return "continue".
    if state["final_output"] is None or state["final_output"] == "":
        return "regenerate"
    else:
        return "continue"
    
def agent_concise_llm_output(state: AgentState):
    print(colored("Generating coherent response", "magenta"))
    try:
        # Input validation and sanitization
        # print(colored("\n[DEBUG] INPUT VALIDATION:", "cyan"))
        initial_request = str(state.get("initial_request", "")).strip()
        final_output = str(state.get("final_output", "")).strip()
        
        if(log_level=="debug"):
            print(f"Initial Request (type: {type(initial_request)}): {repr(initial_request)}")
            print(f"Final Output (type: {type(final_output)}): {repr(final_output)}")
        
        if not initial_request:
            raise ValueError("Initial request is empty or missing")
        if not final_output:
            raise ValueError("Final output is empty or missing")

        generator_input = {
            "initial_request": initial_request,
            "final_output": final_output
        }
        concise_llm_output = concise_output_agent_generator.invoke(generator_input)
        # Response extraction
        # print(colored("\n[DEBUG] RESPONSE EXTRACTION:", "cyan"))
        if isinstance(concise_llm_output, ConciseLLMOutput):
            response = concise_llm_output.message
            # print("Extracted from Pydantic model")
        elif isinstance(concise_llm_output, dict):
            response = concise_llm_output.get('message', '')
            # print("Extracted from dictionary")
        else:
            response = str(concise_llm_output)
            # print("Converted to string")
        
        # print(f"Extracted Response (type: {type(response)}): {repr(response)}")

        # Content validation
        # print(colored("\n[DEBUG] RESPONSE VALIDATION:", "cyan"))
        if not isinstance(response, str):
            raise TypeError(f"Response is {type(response)}, expected string")
            
        if len(response) < 3:
            raise ValueError(f"Response too short: {len(response)} characters")
            
        if final_output not in response:
            raise ValueError(f"Final output '{final_output}' not found in response")

        # Final assignment
        state["concise_llm_output"] = response
        if(log_level=="debug"):
            print(colored("\n[DEBUG] FINAL STATE UPDATE:", "green"))
        print(colored(f"Agent Response: {repr(response)}", "cyan"))

    except Exception as e:
        # Fallback with type safety
        fallback = f"{initial_request} The result is {final_output}."
        print(colored(f"Agent Response FALLBACK: {repr(fallback)}", "cyan"))
        state["concise_llm_output"] = fallback

    # print(colored("\n=== END CONCISE LLM AGENT ===", "magenta", attrs=["bold"]))
    return state