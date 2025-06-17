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

# Ensure this import works when called from bin/eui.py where src is in sys.path
from utils.custom_logging import setup_custom_logging, log_node_ctx

# --- Helper Functions ---
def find_scene_name(code_string): # Stays mostly the same
    match = re.search(r"class\s+([a-zA-Z0-9_]+)\s*\((?:Scene|MovingCameraScene|ZoomedScene|ThreeDScene)\):", code_string)
    if match:
        return match.group(1)
    return None

def log_error_to_markdown(logger: logging.Logger, error_message: str, code_snippet: str, error_md_path: str):
    # Simplified: just ensure directory for error_md_path exists
    try:
        os.makedirs(os.path.dirname(error_md_path), exist_ok=True)
        # Append to the error log file
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

def stream_pipe(pipe, output_list: list, logger: logging.Logger, display_prefix: str = ""): # Stays mostly the same
    try:
        if pipe:
            for line in iter(pipe.readline, ''):
                if display_prefix == "stderr":
                    sys.stderr.write(line) # Stream to actual stderr
                    sys.stderr.flush()
                else:
                    sys.stdout.write(line) # Stream to actual stdout
                    sys.stdout.flush()
                output_list.append(line) # Collect for logging if needed
    except ValueError:
        logger.info(f"Stream pipe '{display_prefix or 'stdout'}' closed abruptly.")
    except Exception as e:
        logger.error(f"Error in stream_pipe ({display_prefix or 'stdout'}): {e}", exc_info=True)


def _trigger_single_render(
    logger: logging.Logger,
    animation_code: str,
    scene_name: str,
    temp_script_path: str,
    manim_media_output_for_command: str, # Specific media dir for this Manim call
    error_logging_path: str,
    project_root_cwd: str # CWD for Manim
    ) -> bool:
    # This function will encapsulate a single Manim call
    # It will run Manim with cwd=project_root_cwd
    # and --media_dir pointing to manim_media_output_for_command

    with log_node_ctx(logger, f"Rendering Scene: {scene_name} using script {temp_script_path}"):
        try:
            with open(temp_script_path, 'w', encoding='utf-8') as f:
                f.write(animation_code)
        except IOError as e:
            logger.error(f"Error writing to temporary file {temp_script_path}: {e}", exc_info=True)
            log_error_to_markdown(logger, f"Failed to write to temporary script: {e}", animation_code, error_logging_path)
            return False

        command = [
            "manim", "render",
            temp_script_path, scene_name,
            "--media_dir", manim_media_output_for_command,
            "-r", "1080,1920",
            # "--progress_bar", "none", # Disables live progress bar
            # "-ql" # Low quality for speed, consider -qm, -qh
        ]
        logger.info(f"Executing in CWD '{project_root_cwd}': {' '.join(command)}")
        
        stdout_lines: list[str] = []
        stderr_lines: list[str] = []
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
                stdout_thread = threading.Thread(target=stream_pipe, args=(process.stdout, stdout_lines, logger, "stdout"))
                stdout_thread.daemon = True 
                stdout_thread.start()

            if process.stderr:
                stderr_thread = threading.Thread(target=stream_pipe, args=(process.stderr, stderr_lines, logger, "stderr"))
                stderr_thread.daemon = True
                stderr_thread.start()

            if process: process.wait() # Wait for Popen to complete.

            # Ensure threads complete by joining them
            if stdout_thread and stdout_thread.is_alive(): stdout_thread.join(timeout=5)
            if stderr_thread and stderr_thread.is_alive(): stderr_thread.join(timeout=5)

            if process and process.returncode == 0:
                logger.info(f"Manim execution successful for: {scene_name}")
                render_successful = True
            else:
                error_code = process.returncode if process else 'N/A'
                error_summary = f"Manim process exited with error code {error_code} for scene: {scene_name}."
                logger.error(error_summary)
                full_error_message_for_md = f"Manim process exited with error code {error_code}.\n"
                full_error_message_for_md += "Stdout:\n" + "".join(stdout_lines) + "\n"
                full_error_message_for_md += "Stderr:\n" + "".join(stderr_lines)
                log_error_to_markdown(logger, full_error_message_for_md, animation_code, error_logging_path)
                render_successful = False

        except KeyboardInterrupt:
            logger.warning("Interruption detected during Manim process. Terminating...")
            if process and process.poll() is None: process.terminate()
            raise 
        except FileNotFoundError:
            error_msg = "FATAL ERROR: 'manim' command not found. Ensure Manim is installed and accessible."
            logger.critical(error_msg)
            log_error_to_markdown(logger, error_msg, animation_code, error_logging_path)
            return False
        except Exception as e:
            error_msg = f"An unexpected error occurred running Manim for {scene_name}: {e}"
            logger.error(error_msg, exc_info=True)
            log_error_to_markdown(logger, error_msg, animation_code, error_logging_path)
            if process and process.poll() is None: process.terminate()
            render_successful = False
        finally:
            if process:
                if process.stdout and not process.stdout.closed: process.stdout.close()
                if process.stderr and not process.stderr.closed: process.stderr.close()

        return render_successful


def render_manim_scenes(code_md_path: str, final_manim_output_media_dir: str, project_root_path: str, cli_logger: logging.Logger):
    logger = cli_logger # Use the logger passed from the CLI for consistent logging

    error_md_log_path = os.path.join(os.path.dirname(final_manim_output_media_dir), "render_manim_errors.md")
    # Ensure parent directory of final_manim_output_media_dir exists, so error log path is valid
    if not os.path.exists(os.path.dirname(final_manim_output_media_dir)):
        os.makedirs(os.path.dirname(final_manim_output_media_dir), exist_ok=True)


    try:
        # Clear/initialize error log at the beginning of a render batch
        with open(error_md_log_path, 'w', encoding='utf-8') as f:
            f.write("# Manim Render Errors Log\n\n")
    except IOError as e:
        logger.error(f"Could not initialize error log file {error_md_log_path}: {e}")

    if not os.path.exists(code_md_path):
        logger.error(f"Markdown file with Manim code not found at '{code_md_path}'")
        return False

    try:
        with open(code_md_path, 'r', encoding='utf-8') as f:
            content = f.read()
        code_pattern = r"```(?:python)?\s*\n(.*?)\n```" # Standard markdown code block
        animations = re.findall(code_pattern, content, re.DOTALL)
    except Exception as e:
        logger.error(f"Error reading or parsing Markdown file '{code_md_path}': {e}", exc_info=True)
        return False

    if not animations:
        logger.info(f"No Python code blocks found in '{code_md_path}'. Nothing to render.")
        return True

    total_animations = len(animations)
    logger.info(f"Found {total_animations} animation code block(s) to process from {code_md_path}.")

    all_scenes_processed_successfully = True # Tracks if all scenes attempted were successful

    with tempfile.TemporaryDirectory(prefix="manim_render_run_") as main_temp_dir:
        temp_scripts_dir = os.path.join(main_temp_dir, "scripts")
        temp_manim_native_output_dir = os.path.join(main_temp_dir, "manim_media_out")
        os.makedirs(temp_scripts_dir, exist_ok=True)
        os.makedirs(temp_manim_native_output_dir, exist_ok=True)
        logger.info(f"Main temporary directory for this run: {main_temp_dir}")

        for i, raw_code in enumerate(animations):
            with log_node_ctx(logger, f"Processing Animation Block {i + 1} of {total_animations}"):
                code = textwrap.dedent(raw_code).strip()
                if not code:
                    logger.warning("Found an empty code block. Skipping.")
                    continue

                scene_name = find_scene_name(code)
                if not scene_name:
                    logger.warning("Could not determine Scene name from code block. Skipping.")
                    log_error_to_markdown(logger, "Could not determine Scene name from code snippet.", code, error_md_log_path)
                    all_scenes_processed_successfully = False
                    continue

                logger.info(f"Identified Scene: {scene_name}")
                # Use a unique name for the temp script file to avoid clashes if scene names are reused
                temp_script_file_path = os.path.join(temp_scripts_dir, f"scene_{i+1}_{scene_name}.py")

                scene_render_success = _trigger_single_render(
                    logger,
                    code,
                    scene_name,
                    temp_script_file_path,
                    temp_manim_native_output_dir,
                    error_md_log_path,
                    project_root_path
                )
                if not scene_render_success:
                    all_scenes_processed_successfully = False

        # After all scenes, move generated media to the final destination
        if os.path.exists(temp_manim_native_output_dir) and any(os.scandir(temp_manim_native_output_dir)):
            logger.info(f"Moving rendered media from temporary location {temp_manim_native_output_dir} to final destination {final_manim_output_media_dir}")
            try:
                # Ensure final_manim_output_media_dir parent exists
                os.makedirs(os.path.dirname(final_manim_output_media_dir), exist_ok=True)
                if os.path.exists(final_manim_output_media_dir):
                    shutil.rmtree(final_manim_output_media_dir) # Clean destination first

                # Instead of copytree then rmtree on source, just move the directory if possible,
                # or copy contents then remove temp. For simplicity with temp dir, copy then let temp dir cleanup.
                shutil.copytree(temp_manim_native_output_dir, final_manim_output_media_dir, dirs_exist_ok=True)
                logger.info(f"Media successfully copied to {final_manim_output_media_dir}")
            except Exception as e:
                logger.error(f"Error moving/copying Manim output from {temp_manim_native_output_dir} to {final_manim_output_media_dir}: {e}", exc_info=True)
                all_scenes_processed_successfully = False # Crucial step failed
        else:
            logger.warning(f"Manim's temporary output directory {temp_manim_native_output_dir} is empty or does not exist. No media to move.")
            # This might be okay if no scenes were supposed to produce video/image output, or if all failed.

    logger.info("Manim scene rendering process finished for all code blocks.")
    if not all_scenes_processed_successfully:
        logger.warning("One or more Manim scenes failed to render or encountered errors. Check logs and error markdown file.")

    return all_scenes_processed_successfully