import json
import os
import subprocess
import tempfile
import logging
import threading
from contextlib import contextmanager
from typing import TypedDict, Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END

_indent_storage = threading.local()

def _get_level():
    return getattr(_indent_storage, 'level', 0)

def increase_indent():
    _indent_storage.level = _get_level() + 1

def decrease_indent():
    _indent_storage.level = max(0, _get_level() - 1)

def get_indent_str():
    return "    " * _get_level()

logger = logging.getLogger("ManimAgent")

class ColoredIndentedFormatter(logging.Formatter):
    GREY = "\x1b[38;20m"
    GREEN = "\x1b[32;20m"
    YELLOW = "\x1b[33;20m"
    RED = "\x1b[31;20m"
    BOLD_RED = "\x1b[31;1m"
    RESET = "\x1b[0m"
    
    BASE_FORMAT = "%(message)s"

    FORMATS = {
        logging.DEBUG: GREY + BASE_FORMAT + RESET,
        logging.INFO: GREEN + BASE_FORMAT + RESET,
        logging.WARNING: YELLOW + BASE_FORMAT + RESET,
        logging.ERROR: RED + BASE_FORMAT + RESET,
        logging.CRITICAL: BOLD_RED + BASE_FORMAT + RESET,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno, self.BASE_FORMAT)
        formatter = logging.Formatter(log_fmt)
        indent_str = get_indent_str()
        original_message = formatter.format(record)
        indented_message = "\n".join(
            f"{indent_str}{line}" for line in original_message.splitlines()
        )
        return indented_message

def setup_logging():
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(ColoredIndentedFormatter())
    if not logger.handlers:
        logger.addHandler(handler)
        logger.propagate = False

@contextmanager
def log_node(name: str):
    logger.info(f"-> Entering Node: {name}")
    increase_indent()
    try:
        yield
    finally:
        decrease_indent()
        logger.info(f"<- Exiting Node: {name}")


COMMON_ERROR_FILE_PATH = os.path.join(os.getcwd(), "src", "common_error.md")
try:
    with open(COMMON_ERROR_FILE_PATH, "r", encoding="utf-8") as f:
        COMMON_ERROR_CONTENT = f.read()
except FileNotFoundError:
    logger.warning(f"Common error file not found at {COMMON_ERROR_FILE_PATH}. Proceeding without it.")
    COMMON_ERROR_CONTENT = "Common error content not available. Please check the path."

MAX_TYPE_CHECK_RETRIES = 2

class ManimScriptGenerationState(TypedDict):
    animation_description: str
    previous_code: Optional[str]
    constructed_prompt: Optional[str]
    generated_script: Optional[str]
    error_message: Optional[str]
    type_check_error_output: Optional[str]
    current_retry_attempt: int


def prepare_prompt_node(state: ManimScriptGenerationState) -> dict:
    with log_node("prepare_prompt"):
        logger.info("Preparing Prompt...")
        animation_description = state["animation_description"]
        previous_item_code = state.get("previous_code")
        current_attempt_script = state.get("generated_script")
        type_check_feedback = state.get("type_check_error_output")

        context_prompt_parts = []

        if type_check_feedback and current_attempt_script:
            logger.info(f"Retrying with type check feedback. Attempt: {state.get('current_retry_attempt', 0)}")
            context_prompt_parts.append(f"""
#####################################################
The following code was generated for the current animation description ('{animation_description}')
but failed static type checking:

Problematic Code:
'''python
{current_attempt_script}
'''

Static Type Checker Output (Errors):
'''
{type_check_feedback}
'''
Please analyze these errors and provide a corrected Manim script.
Ensure the new script is complete, runnable, and addresses these type errors.
The original animation description is: "{animation_description}"
#####################################################""")
        elif previous_item_code:
            context_prompt_parts.append(f"""
#####################################################
Context from a previously generated animation scene (if available):
Previous Code:
'''python
{previous_item_code}
'''
#####################################################""")

        context_prompt_parts.append(f"""
#####################################################
Common Errors to avoid (Review these carefully):
{COMMON_ERROR_CONTENT}
#####################################################""")

        final_context_prompt = "\n".join(context_prompt_parts)

        prompt = f"""
#####################################################
Generate a complete, runnable Manim Python script for the
following animation description. The script should be a single scene
class that inherits from Scene. Do not include any
explanation, just the code inside a single python code block.
Optimized for youtube shorts; Keep animations at the center;
No code diffes that are too big. Always use simple shapes.
{final_context_prompt}
#####################################################

#####################################################
Current Animation Description:
{animation_description}
#####################################################

make sure the old and new verison have coharance;
the old COULD BE the starting point for the new scean if present. ALSO NOT DEPENDS ON YOU.
"""
        return {"constructed_prompt": prompt, "type_check_error_output": None}


def call_gemini_node(state: ManimScriptGenerationState) -> dict:
    with log_node("call_gemini"):
        logger.info("Calling Gemini...")
        if not os.getenv("GOOGLE_API_KEY"):
            return {"error_message": "GOOGLE_API_KEY environment variable not set.", "generated_script": None}

        prompt = state.get("constructed_prompt")
        if not prompt:
            return {"error_message": "Prompt not constructed.", "generated_script": None}

        model_name_for_langchain = "gemini-2.5-pro-preview-06-05"
        logger.info(f"Using Gemini model with Langchain: {model_name_for_langchain}")

        llm = ChatGoogleGenerativeAI(model=model_name_for_langchain)

        logger.info(f"Attempting Gemini API call for animation: {state['animation_description'][:70]}...")
        try:
            response_message = llm.invoke(prompt)
            generated_code = response_message.content

            if isinstance(generated_code, str):
                cleaned_code = generated_code.strip()
                if cleaned_code.startswith("```python"):
                    cleaned_code = cleaned_code[len("```python"):].strip()
                elif cleaned_code.startswith("```"):
                    cleaned_code = cleaned_code[3:].strip()

                if cleaned_code.endswith("```"):
                    cleaned_code = cleaned_code[:-3].strip()

                if cleaned_code.lower().startswith("python\n"):
                    cleaned_code = cleaned_code[len("python\n"):].lstrip()
                elif cleaned_code.lower().startswith("python "):
                     cleaned_code = cleaned_code[len("python "):].lstrip()

                return {"generated_script": cleaned_code.strip(), "error_message": None}
            else:
                error_msg = f"Unexpected response content type from LLM: {type(generated_code)}"
                logger.error(error_msg)
                return {"error_message": error_msg, "generated_script": None}

        except Exception as e:
            error_msg = f"Error calling Gemini or processing response via Langchain: {e}"
            logger.error(error_msg)
            return {"error_message": error_msg, "generated_script": None}


def static_type_check_node(state: ManimScriptGenerationState) -> dict:
    with log_node("static_type_check"):
        logger.info("Performing Static Type Check...")
        script_to_check = state.get("generated_script")
        current_attempt = state.get("current_retry_attempt", 0)

        if not script_to_check:
            logger.warning("No script generated to type check.")
            return {
                "error_message": state.get("error_message", "No script available for type checking."),
                "type_check_error_output": None,
                "current_retry_attempt": current_attempt
            }

        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding='utf-8') as tmp_script:
                tmp_script.write(script_to_check)
                tmp_script_path = tmp_script.name

            command = ["uv", "run", "pyright", tmp_script_path]
            logger.info(f"Running type checker: {' '.join(command)}")

            result = subprocess.run(command, capture_output=True, text=True, check=False, shell=False)

            os.remove(tmp_script_path)

            if result.returncode == 0:
                logger.info("Type check successful.")
                return {
                    "generated_script": script_to_check,
                    "type_check_error_output": None,
                    "current_retry_attempt": current_attempt,
                    "error_message": None
                }
            else:
                error_message = (result.stderr + "\n\n#######################\n\n" + result.stdout)
                logger.warning(f"Type check failed with status code {result.returncode}.")
                return {
                    "generated_script": script_to_check,
                    "type_check_error_output": (error_message or "Type checker returned an error but no stderr."),
                    "current_retry_attempt": current_attempt + 1,
                    "error_message": None
                }
        except FileNotFoundError:
            error_msg = "Error: 'uv' or 'dmypy' command not found. Make sure it's installed and in your PATH."
            logger.error(error_msg)
            return {
                "generated_script": script_to_check,
                "error_message": error_msg,
                "type_check_error_output": error_msg,
                "current_retry_attempt": current_attempt + 1
            }
        except Exception as e:
            error_msg = f"An unexpected error occurred during type checking: {e}"
            logger.error(error_msg)
            return {
                "generated_script": script_to_check,
                "error_message": error_msg,
                "type_check_error_output": error_msg,
                "current_retry_attempt": current_attempt + 1
            }


def should_retry_or_end(state: ManimScriptGenerationState) -> str:
    with log_node("should_retry_or_end"):
        logger.info("Deciding Next Step After Type Check...")
        type_check_error = state.get("type_check_error_output")
        attempts_made = state.get("current_retry_attempt", 0)

        if not type_check_error:
            logger.info("Type check passed or no error reported. Ending.")
            return END

        logger.warning(f"Type check failed. Attempts made so far: {attempts_made-1 if attempts_made > 0 else 0}. Max retries: {MAX_TYPE_CHECK_RETRIES}.")
        if attempts_made > MAX_TYPE_CHECK_RETRIES:
            logger.error(f"Max retries ({MAX_TYPE_CHECK_RETRIES}) reached. Ending current item processing.")
            return END
        else:
            logger.info(f"Proceeding to retry generation (next attempt will be {attempts_made}).")
            return "prepare_prompt"


workflow = StateGraph(ManimScriptGenerationState)

workflow.add_node("prepare_prompt", prepare_prompt_node)
workflow.add_node("call_gemini", call_gemini_node)
workflow.add_node("static_type_check", static_type_check_node)

workflow.set_entry_point("prepare_prompt")
workflow.add_edge("prepare_prompt", "call_gemini")
workflow.add_edge("call_gemini", "static_type_check")

workflow.add_conditional_edges(
    "static_type_check",
    should_retry_or_end,
    {
        "prepare_prompt": "prepare_prompt",
        END: END
    }
)

manim_script_agent = workflow.compile()


def main():
    script_json_path = os.path.join(os.getcwd(), "script.json")
    output_dir = os.path.join(os.getcwd(), "out")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logger.info(f"Created output directory: {output_dir}")
    code_md_path = os.path.join(output_dir, "code.md")

    with open(code_md_path, 'w', encoding='utf-8') as md_file:
        md_file.write("# Generated Manim Code (with Type Checking)\n\n")
        md_file.write(f"This file contains Manim Python code snippets generated based on animation descriptions. Each script attempts to pass static type checking up to {MAX_TYPE_CHECK_RETRIES} retries.\n\n")

    try:
        with open(script_json_path, 'r', encoding='utf-8') as f:
            script_data = json.load(f)
    except FileNotFoundError:
        logger.error(f"The script file {script_json_path} was not found.")
        return
    except json.JSONDecodeError:
        logger.error(f"Could not decode JSON from {script_json_path}.")
        return

    previous_code_for_context = ""

    with open(code_md_path, 'a', encoding='utf-8') as md_file:
        for index, item in enumerate(script_data):
            animation_description = item.get("animation-description")
            if animation_description:
                logger.info(f"\nProcessing animation description {index + 1}/{len(script_data)} with LangGraph agent...")

                agent_input = ManimScriptGenerationState(
                    animation_description=animation_description,
                    previous_code=previous_code_for_context,
                    constructed_prompt=None,
                    generated_script=None,
                    error_message=None,
                    type_check_error_output=None,
                    current_retry_attempt=0
                )

                final_state = manim_script_agent.invoke(agent_input)

                python_code = final_state.get("generated_script")
                agent_llm_error = final_state.get("error_message")
                final_type_check_error = final_state.get("type_check_error_output")

                md_file.write(f"### Animation Scene {index + 1}\n")
                md_file.write(f"**Description:** {animation_description}\n\n")

                if agent_llm_error:
                    logger.error(f"Agent returned a critical error: {agent_llm_error}")
                    md_file.write(f"**Status:** Generation failed due to agent error.\n\n")
                    md_file.write("```text\n")
                    md_file.write(f"# Error from Agent: {agent_llm_error}\n")
                    md_file.write("```\n\n")
                    previous_code_for_context = ""
                elif final_type_check_error and python_code:
                    # logger.error(f"Script for '{animation_description[:70]}...' generated but FAILED final type check.")
                    md_file.write(f"**Status:** Generated, but FAILED static type checking after {MAX_TYPE_CHECK_RETRIES} retries.\n\n")
                    md_file.write("```python\n")
                    md_file.write(f"# Original animation description: {animation_description}\n")
                    md_file.write(f"# SCRIPT FAILED TYPE CHECKING. LAST ATTEMPT:\n\n")
                    md_file.write(python_code)
                    md_file.write(f"\n\n# --- MYPY ERRORS (from last attempt) ---\n# ")
                    md_file.write("\n# ".join(final_type_check_error.splitlines()))
                    md_file.write("\n# --- END MYPY ERRORS ---")
                    md_file.write("\n```\n\n")
                    previous_code_for_context = python_code
                elif python_code:
                    logger.info(f"Script for '{animation_description[:70]}...' generated successfully (passed type checks).")
                    md_file.write(f"**Status:** Generation successful (passed type checks).\n\n")
                    md_file.write("```python\n")
                    md_file.write(python_code)
                    md_file.write("\n```\n\n")
                    previous_code_for_context = python_code
                else:
                    logger.error(f"Agent did not return a script for '{animation_description[:70]}...' and no explicit error message was set in final state.")
                    md_file.write(f"**Status:** Generation failed (no script produced, no specific error).\n\n")
                    md_file.write("```text\n")
                    md_file.write("# Error: No script generated by agent and no specific error message in final state.\n")
                    md_file.write("```\n\n")
                    previous_code_for_context = ""

                logger.info(f"Appended result for scene {index + 1} to {code_md_path}")
            else:
                logger.warning(f"No 'animation-description' found for item {index + 1}.")

    logger.info(f"\nProcessing complete. Manim Python code snippets (with type checking attempts) appended to {code_md_path}")


if __name__ == "__main__":
    setup_logging()
    if not os.getenv("GOOGLE_API_KEY"):
        logger.error("GOOGLE_API_KEY environment variable not set. Please set it before running.")
    else:
        main()