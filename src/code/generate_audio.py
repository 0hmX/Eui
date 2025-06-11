import os
import json
import subprocess
import sys

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
        return

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
            return
    except FileNotFoundError:
        print(f"Critical error: {script_json_filename} not found at {script_json_path}")
        return
    except json.JSONDecodeError as e:
        print(f"Critical error: Could not decode JSON from {script_json_filename}: {e}")
        return
    except Exception as e:
        print(f"Critical error: An unexpected error occurred while reading {script_json_filename}: {e}")
        return

    if not script_items:
        print(f"No items found in {script_json_filename}. Nothing to process.")
        return

    # 3. Process each script item
    for i, item_entry in enumerate(script_items):
        if not isinstance(item_entry, dict):
            print(f"Warning: Entry {i+1} in {script_json_filename} is not a dictionary. Skipping.")
            continue
        
        speech_text = item_entry.get("speech")

        if not speech_text or not isinstance(speech_text, str):
            print(f"Warning: Entry {i+1} in {script_json_filename} does not have a valid 'speech' string. Skipping.")
            continue
        
        # 4. Define output path in numerical format
        output_filename = f"{i + 1}.wav"
        absolute_output_file_path = os.path.join(absolute_audio_out_dir, output_filename)
        
        print(f"\nProcessing speech {i + 1}/{len(script_items)}: \"{speech_text[:60]}{'...' if len(speech_text) > 60 else ''}\"")
        print(f"Target audio file: {absolute_output_file_path}")

        # 5. Prepare and run the command
        command = [
            "uv", "run", cli_script_name, 
            f'"{speech_text}"',  # Pass speech_text directly without extra quotes if cli_tty.py handles it
            f'"{absolute_output_file_path}"' # Same for file path
        ]
        
        stdout_lines = []
        stderr_lines = []

        try:
            print(f"Executing: {' '.join(command)} (CWD: {chatterbox_dir})")
            # Use Popen for real-time streaming
            process = subprocess.Popen(
                command,
                cwd=chatterbox_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                bufsize=1  # Line-buffered
            )

            # Real-time streaming of stdout
            if process.stdout:
                for line in iter(process.stdout.readline, ''):
                    print(line, end='')
                    sys.stdout.flush() # Ensure immediate printing
                    stdout_lines.append(line)
                process.stdout.close()

            # Real-time streaming of stderr
            if process.stderr:
                for line in iter(process.stderr.readline, ''):
                    sys.stderr.write(line) # Write to stderr stream
                    sys.stderr.flush() # Ensure immediate printing
                    stderr_lines.append(line)
                process.stderr.close()

            process.wait() # Wait for the subprocess to complete

            if process.returncode == 0:
                print(f"\nSuccessfully generated: {absolute_output_file_path}")
            else:
                print(f"\nERROR: Failed to generate audio for: \"{speech_text[:60]}...\"")
                print(f"Command failed with exit code {process.returncode}: {' '.join(command)}")
                # Full output already streamed, but can be summarized if needed
                # if stdout_lines:
                #     print(f"Stdout from failed command:\n---\n{''.join(stdout_lines).strip()}\n---")
                # if stderr_lines:
                #     print(f"Stderr from failed command:\n---\n{''.join(stderr_lines).strip()}\n---")

        except FileNotFoundError:
            print(f"CRITICAL ERROR: 'uv' command not found. Please ensure 'uv' is installed and in your system's PATH.")
            print(f"Failed to generate audio for: \"{speech_text[:60]}...\"")
            print("Aborting further processing.")
            return 
        except Exception as e: # Catch other potential errors during Popen or stream handling
            print(f"An unexpected error occurred while processing speech {i + 1} (\"{speech_text[:60]}...\"): {e}")
            # Log full stdout/stderr if available
            if stdout_lines:
                 print(f"Stdout collected before error:\n---\n{''.join(stdout_lines).strip()}\n---")
            if stderr_lines:
                print(f"Stderr collected before error:\n---\n{''.join(stderr_lines).strip()}\n---")
            
    print("\nScript finished. All speech processing tasks have been attempted.")

if __name__ == "__main__":
    main()