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
        # Overwrite/clear the error file for the new error
        with open(error_md_path, 'w', encoding='utf-8') as f:
            f.write("") # Clear the file before writing new error
    except IOError as e:
        print(f"Critical: Could not clear error log file {error_md_path}: {e}")
        # If clearing fails, we still attempt to append, though it might duplicate headers.
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
    for YouTube Shorts (1080x1920). Streams output and logs errors to error.md.
    """
    try:
        with open(temp_script_path, 'w', encoding='utf-8') as f:
            f.write(animation_code)
    except IOError as e:
        print(f"Error writing to temporary file {temp_script_path}: {e}")
        log_error_to_markdown(f"Failed to write to temporary script: {e}", animation_code)
        return

    command = [
        "manim", "render", temp_script_path, scene_name,
        "-r", "1080,1920"
    ]

    print(f"Executing: {' '.join(command)}")
    
    # Store stdout and stderr lines to log them in case of an error
    stdout_lines = []
    stderr_lines = []

    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', bufsize=1)

        # Real-time streaming of stdout
        if process.stdout:
            for line in iter(process.stdout.readline, ''):
                print(line, end='')
                stdout_lines.append(line)
            process.stdout.close()

        # Real-time streaming of stderr
        if process.stderr:
            for line in iter(process.stderr.readline, ''):
                sys.stderr.write(line) # Write to stderr stream
                stderr_lines.append(line)
            process.stderr.close()

        process.wait() # Wait for the subprocess to complete

        if process.returncode != 0:
            error_message = f"Manim process exited with error code {process.returncode}.\n"
            error_message += "Stdout:\n" + "".join(stdout_lines) + "\n"
            error_message += "Stderr:\n" + "".join(stderr_lines)
            print(f"\nError during Manim execution: {scene_name}")
            log_error_to_markdown(error_message, animation_code)
        else:
            print(f"\nManim execution successful for: {scene_name}")
            # Optionally, you can still print full stdout/stderr if needed for successful runs,
            # but it might be redundant if already streamed.
            # if "".join(stdout_lines).strip():
            #     print("Manim Output (Summary):\n", "".join(stdout_lines))
            # if "".join(stderr_lines).strip():
            #     print("Manim Stderr (Warnings/Info Summary):\n", "".join(stderr_lines))


    except FileNotFoundError:
        error_msg = "FATAL ERROR: 'manim' command not found. Please ensure Manim is installed and accessible in your system's PATH."
        print(f"\n{error_msg}")
        log_error_to_markdown(error_msg, animation_code)
    except Exception as e:
        error_msg = f"An unexpected error occurred while trying to run subprocess: {e}"
        print(error_msg)
        log_error_to_markdown(error_msg, animation_code)

def main():
    cwd = os.getcwd()
    code_md_path = os.path.join(cwd, "out", "code.md")
    # error_md_path is defined in log_error_to_markdown, ensure it's consistent if used elsewhere
    # error_md_path = os.path.join(cwd, "out", "error.md") 

    if not os.path.exists(code_md_path):
        print(f"Error: Markdown file not found at '{code_md_path}'")
        sys.exit(1)

    try:
        with open(code_md_path, 'r', encoding='utf-8') as f:
            content = f.read()

        code_pattern = r"```(?:python)?\s*\n(.*?)\n```"
        animations = re.findall(code_pattern, content, re.DOTALL)

    except Exception as e:
        print(f"Error reading or parsing Markdown file '{code_md_path}': {e}")
        sys.exit(1)

    if not animations:
        print(f"No Python code blocks (e.g., ```python ... ```) found in '{code_md_path}'.")
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
                # Log this as an error as well, as it prevents rendering
                log_error_to_markdown(f"Could not determine Scene name from code snippet.", code)
                continue

            print(f"Found Scene: {scene_name}")

            temp_script_path = os.path.join(temp_dir, f"temp_animation_scene_{i}.py")

            trigger_render(code, scene_name, temp_script_path)
            
    print("\nScript finished. All render commands have been attempted.")
    print("Check Manim's default 'media' directory for output videos and 'out/error.md' for any render issues.")
    print("Temporary directory and script files have been cleaned up automatically.")

if __name__ == "__main__":
    main()