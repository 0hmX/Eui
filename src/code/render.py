import sys
import os
import subprocess
import re
import textwrap
import tempfile
import threading
import time

def find_scene_name(code_string):
    match = re.search(r"class\s+([a-zA-Z0-9_]+)\s*\((?:Scene|MovingCameraScene|ZoomedScene|ThreeDScene)\):", code_string)
    if match:
        return match.group(1)
    return None

def log_error_to_markdown(error_message, code_snippet, error_md_path="out\\error.md"):
    try:
        # Clear the error log file by opening in write mode first
        with open(error_md_path, 'w', encoding='utf-8') as f:
            f.write("") 
    except IOError as e:
        print(f"Critical: Could not clear error log file {error_md_path}: {e}")
        # Continue to attempt appending even if clearing failed
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

def stream_pipe(pipe, output_list, display_prefix=""):
    """Reads from a pipe and appends to a list, optionally displaying lines."""
    try:
        if pipe:
            for line in iter(pipe.readline, ''):
                if display_prefix == "stderr":
                    sys.stderr.write(line)
                    sys.stderr.flush()
                else:
                    print(line, end='')
                    sys.stdout.flush()
                output_list.append(line)
    except ValueError: # Pipe might be closed unexpectedly
        if display_prefix:
            print(f"\nInfo: {display_prefix} stream pipe closed abruptly.", file=sys.stderr)
        else:
            print(f"\nInfo: stdout stream pipe closed abruptly.", file=sys.stderr)
    except Exception as e:
        print(f"\nError in stream_pipe ({display_prefix or 'stdout'}): {e}", file=sys.stderr)

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
    stdout_thread = None
    stderr_thread = None

    try:
        process = subprocess.Popen(
            command, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True, 
            encoding='utf-8', 
            bufsize=1
        )

        if process.stdout:
            stdout_thread = threading.Thread(target=stream_pipe, args=(process.stdout, stdout_lines))
            stdout_thread.daemon = True 
            stdout_thread.start()

        if process.stderr:
            stderr_thread = threading.Thread(target=stream_pipe, args=(process.stderr, stderr_lines, "stderr"))
            stderr_thread.daemon = True
            stderr_thread.start()

        if process:
            process.wait()

        if stdout_thread and stdout_thread.is_alive():
            stdout_thread.join(timeout=2)
        if stderr_thread and stderr_thread.is_alive():
            stderr_thread.join(timeout=2)

        if process and process.returncode != 0:
            error_message = f"Manim process exited with error code {process.returncode}.\n"
            error_message += "Stdout:\n" + "".join(stdout_lines) + "\n"
            error_message += "Stderr:\n" + "".join(stderr_lines)
            print(f"\nError during Manim execution: {scene_name}")
            log_error_to_markdown(error_message, animation_code)
        elif process:
            print(f"\nManim execution successful for: {scene_name}")

    except KeyboardInterrupt:
        print("\nInterruption detected during Manim process. Terminating...")
        if process and process.poll() is None:
            print("Sending SIGTERM to Manim process...")
            process.terminate()
            try:
                process.wait(timeout=10)
                print("Manim process terminated gracefully.")
            except subprocess.TimeoutExpired:
                print("Manim process did not terminate gracefully after 10s, sending SIGKILL.")
                process.kill()
                try:
                    process.wait(timeout=5)
                    print("Manim process killed.")
                except subprocess.TimeoutExpired:
                    print("Failed to kill Manim process even after SIGKILL.")
                except Exception as e_kill:
                    print(f"Error during process kill: {e_kill}")
            except Exception as e_term:
                print(f"Error during process termination: {e_term}")
        
        if stdout_thread and stdout_thread.is_alive():
            print("Waiting for stdout stream to close...")
            stdout_thread.join(timeout=5)
            if stdout_thread.is_alive(): print("Stdout stream did not close in time.")
        if stderr_thread and stderr_thread.is_alive():
            print("Waiting for stderr stream to close...")
            stderr_thread.join(timeout=5)
            if stderr_thread.is_alive(): print("Stderr stream did not close in time.")
        
        print("Manim process and stream handling concluded after interruption.")
        raise 
    except FileNotFoundError:
        error_msg = "FATAL ERROR: 'manim' command not found. Please ensure Manim is installed and accessible in your system's PATH."
        print(f"\n{error_msg}")
        log_error_to_markdown(error_msg, animation_code)
    except Exception as e:
        error_msg = f"An unexpected error occurred while trying to run subprocess: {e}"
        print(f"\n{error_msg}")
        log_error_to_markdown(error_msg, animation_code)
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        if stdout_thread and stdout_thread.is_alive():
            stdout_thread.join(timeout=2)
        if stderr_thread and stderr_thread.is_alive():
            stderr_thread.join(timeout=2)
    finally:
        if process:
            if process.stdout and not process.stdout.closed:
                try: process.stdout.close()
                except Exception: pass
            if process.stderr and not process.stderr.closed:
                try: process.stderr.close()
                except Exception: pass
        # Daemon threads will exit with the main thread if still alive.

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
        # Ensure the error log is cleared once before any animations start
        log_error_to_markdown("", "") # Call with empty messages to effectively clear/initialize the log

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