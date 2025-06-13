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
        print(f"Error reading stream ({display_prefix or 'stdout'}): {e}", file=sys.stderr)


def main():
    # Assuming this script is run from the project root directory 
    # (e.g., c:\Users\ankan\Documents\Projects\Eui)
    project_root = os.getcwd() 
    
    script_json_filename = "script.json"
    script_json_path = os.path.join(project_root, script_json_filename)
    
    # Relative path for the audio output directory from the project root
    audio_output_rel_dir = os.path.join("out", "audio")
    absolute_audio_out_dir = os.path.join(project_root, audio_output_rel_dir)
    
    # Path to the chatterbox directory from the project root
    chatterbox_dir = os.path.join(project_root, "chatterbox")
    cli_script_name = "cli_tty.py" # The script to be run within chatterbox_dir

    # 1. Create the output directory if it doesn't exist
    try:
        os.makedirs(absolute_audio_out_dir, exist_ok=True)
        print(f"Output directory ensured at: {absolute_audio_out_dir}")
    except OSError as e:
        print(f"Critical error: Could not create directory {absolute_audio_out_dir}: {e}")
        sys.exit(1)

    # 2. Open and read the script.json file
    script_items = []
    try:
        with open(script_json_path, 'r', encoding='utf-8') as f:
            content = json.load(f)
        if isinstance(content, list):
            script_items = content
            print(f"Successfully read {len(script_items)} entries from {script_json_filename}.")
        else:
            print(f"Error: Content of {script_json_filename} is not a list of items as expected.")
            sys.exit(1)
    except FileNotFoundError:
        print(f"Critical error: {script_json_filename} not found at {script_json_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Critical error: Could not decode JSON from {script_json_filename}: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Critical error: An unexpected error occurred while reading {script_json_filename}: {e}")
        sys.exit(1)

    if not script_items:
        print(f"No items found in {script_json_filename}. Nothing to process.")
        sys.exit(0)

    # 3. Process each script item
    try:
        for i, item_entry in enumerate(script_items):
            if not isinstance(item_entry, dict):
                print(f"Warning: Entry {i+1} in {script_json_filename} is not a dictionary. Skipping.")
                continue
            
            speech_text = item_entry.get("speech")

            if not speech_text or not isinstance(speech_text, str):
                print(f"Warning: Entry {i+1} in {script_json_filename} does not have a valid 'speech' string. Skipping.")
                continue
            
            # 4. Define output path in numerical format
            output_filename = f"{i + 1}.mp3"
            absolute_output_file_path = os.path.join(absolute_audio_out_dir, output_filename)
            
            print(f"\nProcessing speech {i + 1}/{len(script_items)}: \"{speech_text[:60]}{'...' if len(speech_text) > 60 else ''}\"")
            print(f"Target audio file: {absolute_output_file_path}")

            # 5. Prepare and run the command
            command = [
                "uv", "run", cli_script_name, 
                speech_text,
                absolute_output_file_path
            ]
            
            stdout_lines = []
            stderr_lines = []
            process = None # Initialize process to None

            try:
                print(f"Executing: {' '.join(command)} (CWD: {chatterbox_dir})")
                process = subprocess.Popen(
                    command,
                    cwd=chatterbox_dir,
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

                # Wait for threads to finish (which means pipes have been closed)
                if stdout_thread:
                    stdout_thread.join()
                if stderr_thread:
                    stderr_thread.join()
                
                process.wait() # Wait for the subprocess to complete

                if process.returncode == 0:
                    print(f"\nSuccessfully generated: {absolute_output_file_path}")
                else:
                    print(f"\nERROR: Failed to generate audio for: \"{speech_text[:60]}...\"")
                    print(f"Command failed with exit code {process.returncode}: {' '.join(command)}")
                    # Output was already streamed in real-time

            except FileNotFoundError:
                print(f"CRITICAL ERROR: 'uv' command not found. Ensure 'uv' is installed and in PATH.")
                print(f"Failed to generate audio for: \"{speech_text[:60]}...\"")
                print("Aborting further processing.")
                if process: 
                    if stdout_thread and stdout_thread.is_alive(): stdout_thread.join(timeout=1) # type: ignore
                    if stderr_thread and stderr_thread.is_alive(): stderr_thread.join(timeout=1) # type: ignore
                    process.terminate()
                    process.wait()
                sys.exit(1)
            except Exception as e: 
                print(f"An unexpected error occurred while processing speech {i + 1} (\"{speech_text[:60]}...\"): {e}")
                if process: 
                    if stdout_thread and stdout_thread.is_alive(): stdout_thread.join(timeout=1) # type: ignore
                    if stderr_thread and stderr_thread.is_alive(): stderr_thread.join(timeout=1) # type: ignore
                    process.terminate()
                    process.wait()
                # Continue to the next item or sys.exit(1) if critical
            finally:
                if process and process.poll() is None: 
                    print(f"\nEnsuring active subprocess for speech {i+1} is terminated...")
                    if stdout_thread and stdout_thread.is_alive(): # type: ignore
                        # stdout_thread.join(timeout=1) # Give a chance to finish
                        pass # Pipe should close on process.terminate()
                    if stderr_thread and stderr_thread.is_alive(): # type: ignore
                        # stderr_thread.join(timeout=1)
                        pass # Pipe should close on process.terminate()
                    
                    process.terminate()
                    try:
                        process.wait(timeout=5) 
                    except subprocess.TimeoutExpired:
                        print(f"Subprocess for speech {i+1} did not terminate gracefully, killing.")
                        process.kill()
                        process.wait()
                    print("Subprocess terminated.")
                    # Ensure threads are joined after process termination attempt
                    if stdout_thread and stdout_thread.is_alive(): stdout_thread.join(timeout=1) # type: ignore
                    if stderr_thread and stderr_thread.is_alive(): stderr_thread.join(timeout=1) # type: ignore

                        
        print("\nScript finished. All speech processing tasks have been attempted.")

    except KeyboardInterrupt:
        print("\n\nCtrl+C detected. Terminating script and any active subprocesses...")
        # The 'finally' block within the loop should handle individual subprocess termination.
        # If a process is active, its 'finally' block will be triggered upon thread interruption.
        print("Script terminated by user.")
        sys.exit(130) # Standard exit code for Ctrl+C

if __name__ == "__main__":
    main()