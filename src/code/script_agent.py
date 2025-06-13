import os
import json
import argparse
import logging
import threading
from contextlib import contextmanager
from typing import TypedDict, List as PyList, Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
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

logger = logging.getLogger("ScriptGenerator")

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


GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
VIDEO_PROMPT_FILE = os.path.join(os.getcwd(), "src", "generate_video_prompt.md")
DEFAULT_OUTPUT_SCRIPT_FILE = os.path.join(os.getcwd(), "script.json")


class ScriptGenerationState(TypedDict):
    topic: str
    video_prompt_template_content: str
    generated_script_str: Optional[str]
    parsed_script: Optional[PyList[dict]]
    error_message: Optional[str]


def load_video_prompt_template(state: ScriptGenerationState) -> ScriptGenerationState:
    with log_node("load_video_prompt_template"):
        logger.info(f"Loading Video Prompt Template from: {VIDEO_PROMPT_FILE}")
        try:
            with open(VIDEO_PROMPT_FILE, 'r', encoding='utf-8') as f:
                content = f.read()
            
            example_marker = "example output"
            if example_marker in content.lower():
                content = content.split(example_marker)[0].strip()

            lines = content.splitlines()
            if lines and "make a yt-short on the topic" in lines[0].lower():
                content = "\n".join(lines[1:]).strip()

            if not content:
                error_msg = f"Video prompt template file '{VIDEO_PROMPT_FILE}' is empty or relevant content is missing."
                logger.error(error_msg)
                return {**state, "error_message": error_msg, "video_prompt_template_content": ""}

            logger.info("Successfully loaded video prompt template content.")
            return {**state, "video_prompt_template_content": content, "error_message": None}
        except FileNotFoundError:
            error_msg = f"Video prompt template file '{VIDEO_PROMPT_FILE}' not found."
            logger.error(error_msg)
            return {**state, "error_message": error_msg, "video_prompt_template_content": ""}
        except Exception as e:
            error_msg = f"Error loading video prompt template: {str(e)}"
            logger.error(error_msg)
            return {**state, "error_message": error_msg, "video_prompt_template_content": ""}


def generate_script(state: ScriptGenerationState) -> ScriptGenerationState:
    with log_node("generate_script"):
        logger.info("Generating Video Script...")
        if state.get("error_message") or not state.get("video_prompt_template_content"):
            logger.warning("Skipping script generation due to previous error or missing prompt content.")
            return state

        topic = state["topic"]
        video_prompt_template_content = state["video_prompt_template_content"]

        llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro-preview-06-05", temperature=0.7)

        prompt_text = f"""
You are an expert scriptwriter for technical YouTube Shorts.
Your task is to generate a complete video script in JSON format based on the provided topic and the following detailed guidelines.

**Topic for the YouTube Short:**
"{topic}"

**Guidelines for Script Generation:**
{video_prompt_template_content}

**Output Format Instructions:**
- The entire output MUST be a single, valid JSON array of script items.
- Start with `[` and end with `]`.
- Each item in the array must be a JSON object with the exact keys: "music-description", "speech", "animation-description", and "duration".
- Do NOT include any text, explanations, or markdown formatting (like ```json ... ```) outside of the JSON array itself.
- Ensure "speech" is optimized for AI TTS (like Chatterbox): avoid "..." ellipses and full ALL CAPS words/phrases unless absolutely necessary for acronyms.
- Ensure "animation-description" is highly descriptive for Manim, assumes simple shapes/text, and that each animation scene starts by drawing a 2D grid.
- Adhere to all constraints mentioned in the guidelines, such as tone, technical depth, item count, etc.
"""

        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an AI assistant that generates video scripts strictly in JSON format according to detailed guidelines."),
            ("human", prompt_text)
        ])

        chain = prompt | llm | StrOutputParser()

        try:
            logger.info(f"Calling Gemini for topic: \"{topic}\"...")
            generated_script_str = chain.invoke({
                "topic": topic,
                "video_prompt_template_content": video_prompt_template_content
            })
            logger.info("Gemini Response Received.")
            return {**state, "generated_script_str": generated_script_str.strip(), "error_message": None}
        except Exception as e:
            error_msg = f"Error during Gemini API call: {str(e)}"
            logger.error(error_msg)
            return {**state, "generated_script_str": None, "error_message": error_msg}


def parse_and_validate_script(state: ScriptGenerationState) -> ScriptGenerationState:
    with log_node("parse_and_validate_script"):
        logger.info("Parsing and Validating Script...")
        if state.get("error_message") or not state.get("generated_script_str"):
            logger.warning("Skipping parsing due to previous error or no script generated.")
            return state

        script_str = state["generated_script_str"]
        if not script_str:
            error_msg = "No script content received from generation step."
            logger.error(error_msg)
            return {**state, "parsed_script": None, "error_message": error_msg}

        try:
            if script_str.startswith("```json"):
                script_str = script_str[7:]
                if script_str.endswith("```"):
                    script_str = script_str[:-3]
            script_str = script_str.strip()

            if not script_str.startswith("[") or not script_str.endswith("]"):
                raise ValueError("Generated script does not appear to be a JSON list (missing '[' or ']').")

            parsed_json = json.loads(script_str)

            if not isinstance(parsed_json, PyList):
                raise ValueError("Generated script is not a JSON list after parsing.")

            if not parsed_json:
                raise ValueError("Generated script is an empty list.")

            for i, item in enumerate(parsed_json):
                if not isinstance(item, dict):
                    raise ValueError(f"Item {i+1} in the script is not a dictionary.")
                expected_keys = {"music-description", "speech", "animation-description", "duration"}
                actual_keys = set(item.keys())
                if not expected_keys.issubset(actual_keys):
                    missing_keys = expected_keys - actual_keys
                    extra_keys = actual_keys - expected_keys
                    error_detail = f"Item {i+1} is malformed. Missing: {missing_keys if missing_keys else 'None'}. Unexpected: {extra_keys if extra_keys else 'None'}."
                    raise ValueError(error_detail)

            logger.info(f"Successfully parsed and validated script with {len(parsed_json)} items.")
            return {**state, "parsed_script": parsed_json, "error_message": None}
        except json.JSONDecodeError as e:
            error_msg = f"Failed to decode JSON from LLM output: {str(e)}. \nProblematic output snippet (first 500 chars):\n'{script_str[:500]}...'"
            logger.error(error_msg)
            return {**state, "parsed_script": None, "error_message": error_msg}
        except ValueError as e:
            error_msg = f"Validation error in generated script: {str(e)}. \nProblematic output snippet (first 500 chars):\n'{script_str[:500]}...'"
            logger.error(error_msg)
            return {**state, "parsed_script": None, "error_message": error_msg}
        except Exception as e:
            error_msg = f"Unexpected error during script parsing/validation: {str(e)}. \nProblematic output snippet (first 500 chars):\n'{script_str[:500]}...'"
            logger.error(error_msg)
            return {**state, "parsed_script": None, "error_message": error_msg}


workflow = StateGraph(ScriptGenerationState)

workflow.add_node("load_prompt", load_video_prompt_template)
workflow.add_node("generate_script", generate_script)
workflow.add_node("parse_script", parse_and_validate_script)

workflow.set_entry_point("load_prompt")
workflow.add_edge("load_prompt", "generate_script")
workflow.add_edge("generate_script", "parse_script")
workflow.add_edge("parse_script", END)

app = workflow.compile()


def main():
    setup_logging()
    
    if not GOOGLE_API_KEY:
        logger.error("GOOGLE_API_KEY environment variable not set.")
        exit(1)

    parser = argparse.ArgumentParser(description="Generate a video script JSON using AI.")
    parser.add_argument("topic", type=str, help="The topic for the YouTube Short.")
    parser.add_argument(
        "--output",
        type=str,
        default=DEFAULT_OUTPUT_SCRIPT_FILE,
        help=f"Path to save the generated script JSON file (default: {DEFAULT_OUTPUT_SCRIPT_FILE}).",
    )
    args = parser.parse_args()

    logger.info(f"Starting script generation for topic: \"{args.topic}\"")
    logger.info(f"Output will be saved to: {os.path.abspath(args.output)}")

    initial_state = ScriptGenerationState(
        topic=args.topic,
        video_prompt_template_content="",
        generated_script_str=None,
        parsed_script=None,
        error_message=None
    )

    final_state = app.invoke(initial_state)

    if final_state.get("error_message"):
        logger.error("\n--- SCRIPT GENERATION FAILED ---")
        logger.error(f"Error: {final_state['error_message']}")
        return

    if final_state.get("parsed_script"):
        output_path = args.output
        try:
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
                logger.info(f"Created output directory: {output_dir}")

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(final_state["parsed_script"], f, indent=4)
            logger.info("\n--- SCRIPT GENERATION SUCCESSFUL ---")
            logger.info(f"Successfully generated script saved to: {os.path.abspath(output_path)}")
        except IOError as e:
            logger.error("\n--- SCRIPT GENERATION PARTIALLY SUCCESSFUL (FILE ERROR) ---")
            logger.error(f"Error saving script to {output_path}: {str(e)}")
            logger.error("Generated script content (JSON):")
            logger.error(json.dumps(final_state["parsed_script"], indent=4))
        except Exception as e:
            logger.error("\n--- SCRIPT GENERATION PARTIALLY SUCCESSFUL (UNEXPECTED FILE ERROR) ---")
            logger.error(f"Unexpected error saving script: {str(e)}")
            logger.error("Generated script content (JSON):")
            logger.error(json.dumps(final_state["parsed_script"], indent=4))
    else:
        logger.error("\n--- SCRIPT GENERATION FAILED ---")
        logger.error("No script was parsed successfully, and no specific error was reported in the final step.")
        logger.error("This might indicate an issue in the graph logic or an unhandled state.")


if __name__ == "__main__":
    main()