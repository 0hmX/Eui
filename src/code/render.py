#!/usr/bin/env python3
import sys
import os
import subprocess
import re
import textwrap
import tempfile

def find_scene_name(code_string):
    """Finds the Manim scene class name from a string of code."""
    # This regex is robust enough for various class definitions
    match = re.search(r"class\s+([a-zA-Z0-9_]+)\s*\((?:Scene|MovingCameraScene|ZoomedScene|ThreeDScene)\):", code_string)
    if match:
        return match.group(1)
    return None

def log_error_to_markdown(error_message, code_snippet, error_md_path="out\\error.md"):
    """Appends the error message and code snippet to error.md."""
    try:
        with open(error_md_path, 'w', encoding='utf-8') as f:
            f.write("")
    except IOError as e:
        print(f"Critical: Could not write to error log file {error_md_path}: {e}")
    try:
        with open(error_md_path, 'a', encoding='utf-8') as f:
            f.write("### Render Error\n\n")
            f.write("```python\n")
            f.write(code_snippet + "\n")
            f.write("```\n\n")
            f.write("**Error Message:**\n")
            f.write("```\n")
            f.write(error_message + "\n")
            f.write("```\n\n---\n\n")
        print(f"Error logged to {error_md_path}")
    except IOError as e:
        print(f"Critical: Could not write to error log file {error_md_path}: {e}")

def trigger_render(animation_code, scene_name, temp_script_path):
    """
    Writes code to a temporary file and executes the Manim render command
    for YouTube Shorts (1080x1920). Logs errors to error.md without stopping.
    """
    try:
        # The temp_script_path now points to a file inside a temporary directory
        with open(temp_script_path, 'w', encoding='utf-8') as f:
            f.write(animation_code)
    except IOError as e:
        print(f"Error writing to temporary file {temp_script_path}: {e}")
        # Log this preliminary error as well, though it's not a render error
        log_error_to_markdown(f"Failed to write to temporary script: {e}", animation_code)
        return

    command = [
        "manim", "render", temp_script_path, scene_name,
        "-r", "1080,1920"  # Render in FHD for YouTube Shorts
    ]

    print(f"Executing: {' '.join(command)}")
    try:
        # Run the command and capture output
        result = subprocess.run(command, text=True, encoding='utf-8', capture_output=True, check=False)
        
        if result.returncode != 0:
            error_message = f"Manim process exited with error code {result.returncode}.\n"
            error_message += "Stdout:\n" + result.stdout + "\n"
            error_message += "Stderr:\n" + result.stderr
            print(f"Error during Manim execution: {scene_name}")
            log_error_to_markdown(error_message, animation_code)
        else:
            # Print Manim's output (like the progress bar) to the console if successful
            # For simplicity, we'll just print stdout. Stderr might contain warnings.
            if result.stdout:
                print("Manim Output:\n", result.stdout)
            if result.stderr: # Also print stderr in case of warnings even on success
                print("Manim Stderr (Warnings/Info):\n", result.stderr)

    except FileNotFoundError:
        error_msg = "FATAL ERROR: 'manim' command not found. Please ensure Manim is installed and accessible in your system's PATH."
        print(f"\n{error_msg}")
        log_error_to_markdown(error_msg, animation_code)
        # Unlike other errors, if manim isn't found, we probably should stop.
        # However, per requirement, we'll log and attempt to continue, though subsequent renders will also fail.
    except Exception as e:
        error_msg = f"An unexpected error occurred while trying to run subprocess: {e}"
        print(error_msg)
        log_error_to_markdown(error_msg, animation_code)

def main():
    cwd = os.getcwd()
    code_md_path = os.path.join(cwd, "out", "code.md")
    md_file_path = code_md_path

    if not os.path.exists(md_file_path):
        print(f"Error: Markdown file not found at '{md_file_path}'")
        sys.exit(1)

    try:
        with open(md_file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        code_pattern = r"```(?:python)?\s*\n(.*?)\n```"
        animations = re.findall(code_pattern, content, re.DOTALL)

    except Exception as e:
        print(f"Error reading or parsing Markdown file '{md_file_path}': {e}")
        sys.exit(1)

    if not animations:
        print(f"No Python code blocks (e.g., ```python ... ```) found in '{md_file_path}'.")
        sys.exit(0)

    total_animations = len(animations)

    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Created temporary directory for scripts: {temp_dir}")

        for i, raw_code in enumerate(animations):
            print(f"\n--- Triggering Animation {i + 1} of {total_animations} ---")

            code = textwrap.dedent(raw_code).strip()

            if not code:
                print("Warning: Found an empty code block. Skipping.")
                continue

            scene_name = find_scene_name(code)
            if not scene_name:
                print("Warning: Could not determine Scene name from code. Skipping.")
                print(f"Problematic code snippet:\n---\n{code}\n---")
                continue

            print(f"Found Scene: {scene_name}")

            temp_script_path = os.path.join(temp_dir, f"temp_animation_scene_{i}.py")

            trigger_render(code, scene_name, temp_script_path)
    print("\nScript finished. All render commands have been executed.")
    print("Check Manim's default 'media' directory for output videos.")
    print("Temporary directory and script files have been cleaned up automatically.")

if __name__ == "__main__":
    main()