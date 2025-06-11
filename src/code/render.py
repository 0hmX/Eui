import sys
import os
import subprocess
import re
import textwrap
import tempfile

def find_scene_name(code_string):
    match = re.search(r"class\s+([a-zA-Z0-9_]+)\s*\((?:Scene|MovingCameraScene|ZoomedScene|ThreeDScene)\):", code_string)
    if match:
        return match.group(1)
    return None

def log_error_to_markdown(error_message, code_snippet, error_md_path="out\\error.md"):
    try:
        with open(error_md_path, 'w', encoding='utf-8') as f:
            f.write("") 
    except IOError as e:
        print(f"Critical: Could not clear error log file {error_md_path}: {e}")
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
    
    stdout_lines = []
    stderr_lines = []
    process = None

    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', bufsize=1)

        if process.stdout:
            for line in iter(process.stdout.readline, ''):
                print(line, end='')
                stdout_lines.append(line)
            process.stdout.close()

        if process.stderr:
            for line in iter(process.stderr.readline, ''):
                sys.stderr.write(line)
                stderr_lines.append(line)
            process.stderr.close()

        process.wait()

        if process.returncode != 0:
            error_message = f"Manim process exited with error code {process.returncode}.\n"
            error_message += "Stdout:\n" + "".join(stdout_lines) + "\n"
            error_message += "Stderr:\n" + "".join(stderr_lines)
            print(f"\nError during Manim execution: {scene_name}")
            log_error_to_markdown(error_message, animation_code)
        else:
            print(f"\nManim execution successful for: {scene_name}")

    except KeyboardInterrupt:
        print("\nInterruption detected during Manim process. Terminating...")
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print("Manim process did not terminate gracefully, killing.")
                process.kill()
                process.wait()
            print("Manim process terminated.")
        raise 
    except FileNotFoundError:
        error_msg = "FATAL ERROR: 'manim' command not found. Please ensure Manim is installed and accessible in your system's PATH."
        print(f"\n{error_msg}")
        log_error_to_markdown(error_msg, animation_code)
    except Exception as e:
        error_msg = f"An unexpected error occurred while trying to run subprocess: {e}"
        print(error_msg)
        log_error_to_markdown(error_msg, animation_code)

def main():
    try:
        cwd = os.getcwd()
        code_md_path = os.path.join(cwd, "out", "code.md")

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
                    log_error_to_markdown(f"Could not determine Scene name from code snippet.", code)
                    continue

                print(f"Found Scene: {scene_name}")

                temp_script_path = os.path.join(temp_dir, f"temp_animation_scene_{i}.py")

                trigger_render(code, scene_name, temp_script_path)
            
        print("\nScript finished. All render commands have been attempted.")
        print("Check Manim's default 'media' directory for output videos and 'out/error.md' for any render issues.")
        print("Temporary directory and script files have been cleaned up automatically.")

    except KeyboardInterrupt:
        print("\n\nCtrl+C detected. Terminating script.")
        sys.exit(130)

if __name__ == "__main__":
    main()