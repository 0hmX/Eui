import os
import json
import subprocess
import sys
import threading

def stream_output(pipe, output_list, display_prefix=""):
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
            pipe.close()
    except Exception as e:
        # Handle potential errors during stream reading, e.g., if pipe closes unexpectedly
        # Use a logger if available, otherwise print to stderr
        sys.stderr.write(f"Error reading stream ({display_prefix or 'stdout'}): {e}\n")

def generate_audio_from_script(script_json_path: str, output_audio_dir: str, audio_generator_tool_script_path: str, current_project_root: str):
    """
    Generates audio files from a script JSON file using an external audio generation tool.

    Args:
        script_json_path: Path to the input script JSON file.
        output_audio_dir: Directory to save the generated MP3 files.
        audio_generator_tool_script_path: Absolute path to the audio_generator_tool.py script.
        current_project_root: The root directory of the project, used as CWD for subprocess.

    Returns:
        True if all audio files were generated successfully, False otherwise.
    """
    all_successful = True

    # 1. Create the output directory if it doesn't exist
    try:
        os.makedirs(output_audio_dir, exist_ok=True)
        sys.stdout.write(f"Output directory ensured at: {output_audio_dir}\n")
    except OSError as e:
        sys.stderr.write(f"Critical error: Could not create directory {output_audio_dir}: {e}\n")
        return False

    # 2. Open and read the script.json file
    script_items = []
    try:
        with open(script_json_path, 'r', encoding='utf-8') as f:
            content = json.load(f)
        if isinstance(content, list):
            script_items = content
            sys.stdout.write(f"Successfully read {len(script_items)} entries from {os.path.basename(script_json_path)}.\n")
        else:
            sys.stderr.write(f"Error: Content of {os.path.basename(script_json_path)} is not a list of items as expected.\n")
            return False
    except FileNotFoundError:
        sys.stderr.write(f"Critical error: {os.path.basename(script_json_path)} not found at {script_json_path}\n")
        return False
    except json.JSONDecodeError as e:
        sys.stderr.write(f"Critical error: Could not decode JSON from {os.path.basename(script_json_path)}: {e}\n")
        return False
    except Exception as e:
        sys.stderr.write(f"Critical error: An unexpected error occurred while reading {os.path.basename(script_json_path)}: {e}\n")
        return False

    if not script_items:
        sys.stdout.write(f"No items found in {os.path.basename(script_json_path)}. Nothing to process.\n")
        return True # No items to process is not an error in itself for this function

    # 3. Process each script item
    for i, item_entry in enumerate(script_items):
        if not isinstance(item_entry, dict):
            sys.stderr.write(f"Warning: Entry {i+1} in {os.path.basename(script_json_path)} is not a dictionary. Skipping.\n")
            all_successful = False
            continue

        speech_text = item_entry.get("speech")
        scene_number = item_entry.get("scene_number", i + 1) # Use scene_number if present, else index

        if not speech_text or not isinstance(speech_text, str):
            sys.stderr.write(f"Warning: Entry for scene {scene_number} in {os.path.basename(script_json_path)} does not have a valid 'speech' string. Skipping.\n")
            all_successful = False
            continue

        # 4. Define output path using scene_number or index
        output_filename = f"{scene_number}.mp3"
        absolute_output_file_path = os.path.join(output_audio_dir, output_filename)

        sys.stdout.write(f"\nProcessing speech for scene {scene_number} ({i+1}/{len(script_items)}): \"{speech_text[:60]}{'...' if len(speech_text) > 60 else ''}\"\n")
        sys.stdout.write(f"Target audio file: {absolute_output_file_path}\n")

        # 5. Prepare and run the command
        command = [
            "uv", "run", audio_generator_tool_script_path,
            speech_text,
            absolute_output_file_path
        ]

        stdout_lines = []
        stderr_lines = []
        process = None

        try:
            sys.stdout.write(f"Executing: {' '.join(command)}\n")
            process = subprocess.Popen(
                command,
                cwd=current_project_root, # Use specified project root as CWD
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                bufsize=1
            )

            stdout_thread = None
            stderr_thread = None

            if process.stdout:
                stdout_thread = threading.Thread(target=stream_output, args=(process.stdout, stdout_lines))
                stdout_thread.start()

            if process.stderr:
                stderr_thread = threading.Thread(target=stream_output, args=(process.stderr, stderr_lines, "stderr"))
                stderr_thread.start()

            if stdout_thread: stdout_thread.join()
            if stderr_thread: stderr_thread.join()
            
            process.wait()

            if process.returncode == 0:
                sys.stdout.write(f"\nSuccessfully generated: {absolute_output_file_path}\n")
            else:
                sys.stderr.write(f"\nERROR: Failed to generate audio for scene {scene_number}: \"{speech_text[:60]}...\"\n")
                sys.stderr.write(f"Command failed with exit code {process.returncode}: {' '.join(command)}\n")
                all_successful = False

        except FileNotFoundError:
            sys.stderr.write(f"CRITICAL ERROR: 'uv' command not found or '{audio_generator_tool_script_path}' not found. Ensure 'uv' is installed and paths are correct.\n")
            sys.stderr.write(f"Failed to generate audio for scene {scene_number}: \"{speech_text[:60]}...\"\n")
            all_successful = False
            # Do not sys.exit, let the caller decide if it's fatal for the whole pipeline
            return False # This is a critical failure for this function call
        except Exception as e:
            sys.stderr.write(f"An unexpected error occurred while processing speech for scene {scene_number} (\"{speech_text[:60]}...\"): {e}\n")
            all_successful = False
        finally:
            if process and process.poll() is None:
                sys.stdout.write(f"\nEnsuring active subprocess for speech {scene_number} is terminated...\n")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    sys.stderr.write(f"Subprocess for speech {scene_number} did not terminate gracefully, killing.\n")
                    process.kill()
                    process.wait()
                sys.stdout.write("Subprocess terminated.\n")
                if stdout_thread and stdout_thread.is_alive(): stdout_thread.join(timeout=1)
                if stderr_thread and stderr_thread.is_alive(): stderr_thread.join(timeout=1)
                        
    sys.stdout.write("\nAudio generation process finished. All speech processing tasks have been attempted.\n")
    return all_successful