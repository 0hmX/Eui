import sys
import os
import subprocess
import re
import textwrap
import tempfile
import threading
import logging

# Adjust sys.path to find custom_logging
# This assumes the script is in Eui/src/tools and custom_logging.py is in Eui/src/utils
_CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
_SRC_DIR = os.path.dirname(_CURRENT_FILE_DIR) 
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from ..utils.custom_logging import setup_custom_logging, log_node_ctx

def find_scene_name(code_string):
    match = re.search(r"class\s+([a-zA-Z0-9_]+)\s*\((?:Scene|MovingCameraScene|ZoomedScene|ThreeDScene)\):", code_string)
    if match:
        return match.group(1)
    return None

def log_error_to_markdown(logger: logging.Logger, error_message: str, code_snippet: str, error_md_path: str = "out\\error.md"):
    try:
        # Ensure the 'out' directory exists
        os.makedirs(os.path.dirname(error_md_path), exist_ok=True)
        # Clear the error log file by opening in write mode first
        with open(error_md_path, 'w', encoding='utf-8') as f:
            f.write("") 
    except IOError as e:
        logger.critical(f"Could not clear error log file {error_md_path}: {e}")
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
        logger.info(f"Error details logged to {error_md_path}")
    except IOError as e:
        logger.critical(f"Could not write to error log file {error_md_path}: {e}")

def stream_pipe(pipe, output_list: list, logger: logging.Logger, display_prefix: str = ""):
    """Reads from a pipe and appends to a list, optionally displaying lines."""
    try:
        if pipe:
            for line in iter(pipe.readline, ''):
                # Keep direct output for Manim's own formatting
                if display_prefix == "stderr":
                    sys.stderr.write(line)
                    sys.stderr.flush()
                else: # "stdout" or other
                    sys.stdout.write(line)
                    sys.stdout.flush()
                output_list.append(line)
    except ValueError: # Pipe might be closed unexpectedly
        logger.info(f"Stream pipe '{display_prefix or 'stdout'}' closed abruptly.")
    except Exception as e:
        logger.error(f"Error in stream_pipe ({display_prefix or 'stdout'}): {e}", exc_info=True)

def trigger_render(logger: logging.Logger, animation_code: str, scene_name: str, temp_script_path: str):
    with log_node_ctx(logger, f"Rendering Scene: {scene_name}"):
        try:
            with open(temp_script_path, 'w', encoding='utf-8') as f:
                f.write(animation_code)
        except IOError as e:
            logger.error(f"Error writing to temporary file {temp_script_path}: {e}", exc_info=True)
            log_error_to_markdown(logger, f"Failed to write to temporary script: {e}", animation_code)
            return

        command = [
            "manim", "render", temp_script_path, scene_name,
            "-r", "1080,1920" # Example resolution, consider making configurable
        ]

        logger.info(f"Executing: {' '.join(command)}")
        
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
                bufsize=1 # Line buffered
            )

            if process.stdout:
                stdout_thread = threading.Thread(target=stream_pipe, args=(process.stdout, stdout_lines, logger, "stdout"))
                stdout_thread.daemon = True 
                stdout_thread.start()

            if process.stderr:
                stderr_thread = threading.Thread(target=stream_pipe, args=(process.stderr, stderr_lines, logger, "stderr"))
                stderr_thread.daemon = True
                stderr_thread.start()

            if process:
                process.wait() # Wait for the subprocess to complete

            if stdout_thread and stdout_thread.is_alive():
                stdout_thread.join(timeout=2)
            if stderr_thread and stderr_thread.is_alive():
                stderr_thread.join(timeout=2)

            if process and process.returncode != 0:
                error_summary = f"Manim process exited with error code {process.returncode} for scene: {scene_name}."
                logger.error(error_summary + f" Check '{os.path.join('out', 'error.md')}' for full details.")
                
                full_error_message_for_md = f"Manim process exited with error code {process.returncode}.\n"
                full_error_message_for_md += "Stdout:\n" + "".join(stdout_lines) + "\n"
                full_error_message_for_md += "Stderr:\n" + "".join(stderr_lines)
                log_error_to_markdown(logger, full_error_message_for_md, animation_code)
            elif process:
                logger.info(f"Manim execution successful for: {scene_name}")

        except KeyboardInterrupt:
            logger.warning("Interruption detected during Manim process. Terminating...")
            if process and process.poll() is None:
                logger.info("Sending SIGTERM to Manim process...")
                process.terminate()
                try:
                    process.wait(timeout=10)
                    logger.info("Manim process terminated gracefully.")
                except subprocess.TimeoutExpired:
                    logger.warning("Manim process did not terminate gracefully after 10s, sending SIGKILL.")
                    process.kill()
                    try:
                        process.wait(timeout=5)
                        logger.info("Manim process killed.")
                    except subprocess.TimeoutExpired:
                        logger.error("Failed to kill Manim process even after SIGKILL.")
                    except Exception as e_kill:
                        logger.error(f"Error during process kill: {e_kill}", exc_info=True)
                except Exception as e_term:
                    logger.error(f"Error during process termination: {e_term}", exc_info=True)
            
            if stdout_thread and stdout_thread.is_alive():
                logger.info("Waiting for stdout stream to close...")
                stdout_thread.join(timeout=5)
                if stdout_thread.is_alive(): logger.warning("Stdout stream did not close in time.")
            if stderr_thread and stderr_thread.is_alive():
                logger.info("Waiting for stderr stream to close...")
                stderr_thread.join(timeout=5)
                if stderr_thread.is_alive(): logger.warning("Stderr stream did not close in time.")
            
            logger.info("Manim process and stream handling concluded after interruption.")
            raise 
        except FileNotFoundError:
            error_msg = "FATAL ERROR: 'manim' command not found. Please ensure Manim is installed and accessible in your system's PATH."
            logger.critical(error_msg)
            log_error_to_markdown(logger, error_msg, animation_code)
        except Exception as e:
            error_msg = f"An unexpected error occurred while trying to run Manim subprocess: {e}"
            logger.error(error_msg, exc_info=True)
            log_error_to_markdown(logger, error_msg, animation_code)
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

def main():
    logger = setup_custom_logging(logger_name="RenderManimTool", level=logging.INFO)

    try:
        with log_node_ctx(logger, "Main Script Execution"):
            cwd = os.getcwd()
            # Define paths relative to CWD or make them configurable
            out_dir = os.path.join(cwd, "out")
            code_md_path = os.path.join(out_dir, "code.md")
            error_md_path = os.path.join(out_dir, "error.md")
            
            os.makedirs(out_dir, exist_ok=True) # Ensure output directory exists

            if not os.path.exists(code_md_path):
                logger.error(f"Markdown file not found at '{code_md_path}'")
                sys.exit(1)

            try:
                with open(code_md_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                code_pattern = r"```(?:python)?\s*\n(.*?)\n```"
                animations = re.findall(code_pattern, content, re.DOTALL)
            except Exception as e:
                logger.error(f"Error reading or parsing Markdown file '{code_md_path}': {e}", exc_info=True)
                sys.exit(1)

            if not animations:
                logger.info(f"No Python code blocks found in '{code_md_path}'. Exiting.")
                sys.exit(0)

            total_animations = len(animations)
            logger.info(f"Found {total_animations} animation(s) to process.")
            
            log_error_to_markdown(logger, "", "", error_md_path=error_md_path) # Clear/initialize error log

            with tempfile.TemporaryDirectory() as temp_dir:
                logger.info(f"Created temporary directory for scripts: {temp_dir}")

                for i, raw_code in enumerate(animations):
                    with log_node_ctx(logger, f"Processing Animation {i + 1} of {total_animations}"):
                        code = textwrap.dedent(raw_code).strip()
                        if not code:
                            logger.warning("Found an empty code block. Skipping.")
                            continue

                        scene_name = find_scene_name(code)
                        if not scene_name:
                            logger.warning("Could not determine Scene name from code. Skipping.")
                            logger.debug(f"Problematic code snippet:\n---\n{code}\n---")
                            log_error_to_markdown(logger, "Could not determine Scene name from code snippet.", code, error_md_path=error_md_path)
                            continue

                        logger.info(f"Found Scene: {scene_name}")
                        temp_script_path = os.path.join(temp_dir, f"temp_animation_scene_{i}.py")
                        trigger_render(logger, code, scene_name, temp_script_path)
            
            logger.info("Script finished. All render commands have been attempted.")
            logger.info(f"Check Manim's default 'media' directory for output videos and '{error_md_path}' for any render issues.")
            logger.info("Temporary directory and script files have been cleaned up automatically.")

    except KeyboardInterrupt:
        if 'logger' in locals() and logger: # Check if logger was initialized
            logger.warning("Ctrl+C detected. Terminating script.")
        else:
            print("\n\nCtrl+C detected. Terminating script (logger not initialized).")
        sys.exit(130) 
    except Exception as e:
        if 'logger' in locals() and logger:
            logger.critical(f"An unexpected error occurred in main: {e}", exc_info=True)
        else:
            print(f"An unexpected critical error occurred in main (logger not initialized): {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()