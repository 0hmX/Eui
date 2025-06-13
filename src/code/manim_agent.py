import json
import os
from typing import TypedDict, Optional

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END

COMMON_ERROR_FILE_PATH = os.path.join(os.getcwd(), "src", "common_error.md")
try:
    with open(COMMON_ERROR_FILE_PATH, "r", encoding="utf-8") as f:
        COMMON_ERROR_CONTENT = f.read()
except FileNotFoundError:
    print(f"Warning: Common error file not found at {COMMON_ERROR_FILE_PATH}. Proceeding without it.")
    COMMON_ERROR_CONTENT = "Common error content not available. Please check the path."

class ManimScriptGenerationState(TypedDict):
    animation_description: str
    previous_code: Optional[str]
    constructed_prompt: Optional[str]
    generated_script: Optional[str]
    error_message: Optional[str]

def prepare_prompt_node(state: ManimScriptGenerationState) -> dict:
    print("--- Preparing Prompt ---")
    animation_description = state["animation_description"]
    previous_code = state.get("previous_code")

    context_prompt_parts = []
    if previous_code:
        context_prompt_parts.append(f"""
#####################################################
Context from the previous generation:
Previous Code:
'''python
{previous_code}
'''
#####################################################""")
    
    context_prompt = "\n".join(context_prompt_parts)

    prompt = f"""
#####################################################
Generate a complete, runnable Manim Python script for the
following animation description. The script should be a single scene
class that inherits from Scene. Do not include any
explanation, just the code inside a single python code block.
Optimized for youtube shorts; Keep animations at the center;
No code diffes that are too big. Always use simple shapes.
{context_prompt}
#####################################################

#####################################################
Current Animation Description: 
{animation_description}
#####################################################

make sure the old and new verison have coharance;
the old COULD BE the starting point for the new scean if present. ALSO NOT DEPENDS ON YOU.

#####################################################
Common Errors to avoid: 
{COMMON_ERROR_CONTENT}
#####################################################
"""
    return {"constructed_prompt": prompt}

def call_gemini_node(state: ManimScriptGenerationState) -> dict:
    print("--- Calling Gemini ---")
    if not os.getenv("GOOGLE_API_KEY"):
        return {"error_message": "GOOGLE_API_KEY environment variable not set.", "generated_script": None}

    prompt = state.get("constructed_prompt")
    if not prompt:
        return {"error_message": "Prompt not constructed.", "generated_script": None}

    model_name_for_langchain = "gemini-2.5-pro-preview-06-05"
    print(f"Using Gemini model with Langchain: {model_name_for_langchain}")

    llm = ChatGoogleGenerativeAI(model=model_name_for_langchain)
    
    print(f"Attempting Gemini API call for animation: {state['animation_description'][:70]}...")
    try:
        response_message = llm.invoke(prompt)
        generated_code = response_message.content

        if isinstance(generated_code, str):
            cleaned_code = generated_code.strip()
            if cleaned_code.startswith("```python"):
                cleaned_code = cleaned_code[9:]
            if cleaned_code.endswith("```"):
                cleaned_code = cleaned_code[:-3]
            
            if cleaned_code.lower().startswith("python\n"):
                cleaned_code = cleaned_code[len("python\n"):].lstrip()
            elif cleaned_code.lower().startswith("python "):
                 cleaned_code = cleaned_code[len("python "):].lstrip()

            return {"generated_script": cleaned_code.strip(), "error_message": None}
        else:
            error_msg = f"Unexpected response content type from LLM: {type(generated_code)}"
            print(error_msg)
            return {"error_message": error_msg, "generated_script": None}

    except Exception as e:
        error_msg = f"Error calling Gemini or processing response via Langchain: {e}"
        print(error_msg)
        return {"error_message": error_msg, "generated_script": None}

workflow = StateGraph(ManimScriptGenerationState)

workflow.add_node("prepare_prompt", prepare_prompt_node)
workflow.add_node("call_gemini", call_gemini_node)

workflow.set_entry_point("prepare_prompt")
workflow.add_edge("prepare_prompt", "call_gemini")
workflow.add_edge("call_gemini", END)

manim_script_agent = workflow.compile()

def main():
    script_json_path = os.path.join(os.getcwd(), "script.json")
    code_md_path = os.path.join(os.getcwd(), "code.md")

    with open(code_md_path, 'w', encoding='utf-8') as md_file:
        md_file.write("# Generated Manim Code\n\n")
        md_file.write("This file contains Manim Python code snippets generated based on animation descriptions.\n\n")

    try:
        with open(script_json_path, 'r', encoding='utf-8') as f:
            script_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: The script file {script_json_path} was not found.")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {script_json_path}.")
        return

    previous_generated_code = ""

    with open(code_md_path, 'a', encoding='utf-8') as md_file:
        for index, item in enumerate(script_data):
            animation_description = item.get("animation-description")
            if animation_description:
                print(f"\nProcessing animation description {index + 1}/{len(script_data)} with LangGraph agent...")
                
                agent_input = {
                    "animation_description": animation_description,
                    "previous_code": previous_generated_code,
                }

                final_state = manim_script_agent.invoke(agent_input)

                python_code = final_state.get("generated_script")
                agent_error = final_state.get("error_message")

                if agent_error:
                    print(f"Agent returned an error: {agent_error}")
                    python_code = f"# Error from Agent: {agent_error}"
                elif not python_code:
                    print("Agent did not return a script and no explicit error message was set.")
                    python_code = "# Error: No script generated by agent and no specific error."
                
                previous_generated_code = python_code if python_code else ""

                md_file.write(f"### Animation Scene {index + 1}\n")
                md_file.write(f"**Description:** {animation_description}\n\n")
                md_file.write("```python\n")
                md_file.write(python_code if python_code else "# Error: No code was generated.")
                md_file.write("\n```\n\n")
                print(f"Appended code for scene {index + 1} to {code_md_path}")
            else:
                print(f"Warning: No 'animation-description' found for item {index + 1}.")

    print(f"\nProcessing complete. Manim Python code snippets appended to {code_md_path}")

if __name__ == "__main__":
    if not os.getenv("GOOGLE_API_KEY"):
        print("Error: GOOGLE_API_KEY environment variable not set. Please set it before running.")
    else:
        main()