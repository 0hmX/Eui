#!/usr/bin/env python3

import argparse
import os
import sys
import logging
import json
import shutil
import glob # For run_all_pipeline checks
from dotenv import load_dotenv

# Adjust sys.path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, "src"))

try:
    from src.agents.script_agent import app as script_agent_app, ScriptGenerationState
    from src.agents.manim_agent import generate_manim_code_from_script
    from src.tools.audio_tool import generate_audio_from_script
    from src.tools.render_manim_tool import render_manim_scenes
    from src.tools.video_tool import create_video_from_script
    from src.utils.custom_logging import setup_custom_logging
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Please ensure that the 'src' directory is structured correctly and all dependencies are installed.")
    print("It's also possible that some tools (e.g., audio_tool, render_manim_tool) have their own specific dependencies not yet installed.")
    sys.exit(1)

logger = setup_custom_logging(logger_name="EuiCli")

# --- Define command functions (with workarounds for now) ---

def run_generate_script(topic: str, output_path: str) -> bool:
    logger.info(f"Starting script generation for topic: '{topic}' -> {output_path}")
    try:
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        initial_state = ScriptGenerationState(
            topic=topic, video_prompt_template_content="", # Loaded by agent
        generated_script_str=None, parsed_script=None, error_message=None
    )
            generated_script_str=None, parsed_script=None, error_message=None
        )
        # Assuming script_agent_app is a LangGraph compiled app
        final_state = script_agent_app.invoke(initial_state)

        if isinstance(final_state, dict): # LangGraph apps often return dicts
            if final_state.get("error_message"):
                logger.error(f"Script generation failed: {final_state['error_message']}")
                return False
            parsed_script = final_state.get("parsed_script")
            if parsed_script:
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(parsed_script, f, indent=4)
                logger.info(f"Script successfully generated and saved to {output_path}")
                return True
        elif hasattr(final_state, 'parsed_script') and final_state.parsed_script: # If it's an object
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(final_state.parsed_script, f, indent=4)
            logger.info(f"Script successfully generated and saved to {output_path}")
            return True
        elif hasattr(final_state, 'error_message') and final_state.error_message:
            logger.error(f"Script generation failed: {final_state.error_message}")
            return False

        logger.error("Script generation did not produce a parsed script and reported no error. Final state: %s", final_state)
        return False
    except Exception as e:
        logger.exception(f"An unexpected error occurred during script generation for topic '{topic}': {e}")
        return False

def run_generate_manim_code(script_path: str, code_md_path: str) -> bool:
    logger.info(f"Starting Manim code generation from script: '{script_path}' -> {code_md_path}")
    try:
        if not os.path.exists(script_path):
            logger.error(f"Input script {script_path} not found.")
            return False

        success = generate_manim_code_from_script(script_json_path=script_path, output_code_md_path=code_md_path)
        if success:
            logger.info(f"Manim code generation successful. Output at {code_md_path}")
            return True
        else:
            logger.error(f"Manim code generation failed. See agent logs for details. Script: {script_path}, Output: {code_md_path}")
            return False
    except Exception as e:
        logger.exception(f"An unexpected error occurred during Manim code generation: {e}")
        return False

def run_generate_audio(script_path: str, audio_dir: str) -> bool:
    logger.info(f"Starting audio generation from script: '{script_path}' -> {audio_dir}")
    try:
        if not os.path.exists(script_path):
            logger.error(f"Input script {script_path} not found.")
            return False

        audio_generator_script = os.path.join(project_root, "src", "tools", "audio_generator_tool.py")
        if not os.path.exists(audio_generator_script):
            logger.error(f"Audio generator tool script not found at {audio_generator_script}")
            return False

        os.makedirs(audio_dir, exist_ok=True)

        success = generate_audio_from_script(
            script_json_path=script_path,
            output_audio_dir=audio_dir,
            audio_generator_tool_script_path=audio_generator_script,
            current_project_root=project_root
        )
        if success:
            logger.info(f"Audio generation process completed. Output potentially in {audio_dir}")
            if not os.listdir(audio_dir): # Check if directory is empty
                 logger.warning(f"Audio generation reported success, but output directory {audio_dir} is empty.")
            return True # Still return true as the tool itself might not consider empty output an error
        else:
            logger.error(f"Audio generation failed. See tool logs for details. Script: {script_path}, Output dir: {audio_dir}")
            return False
    except Exception as e:
        logger.exception(f"An unexpected error occurred during audio generation: {e}")
        return False

def run_render_video(code_md_path: str, media_dir_target: str) -> bool:
    logger.info(f"Starting Manim scene rendering from code: '{code_md_path}' -> {media_dir_target}")
    try:
        if not os.path.exists(code_md_path):
            logger.error(f"Input Manim code file {code_md_path} not found.")
            return False

        media_dir_parent = os.path.dirname(media_dir_target)
        if not os.path.exists(media_dir_parent):
            os.makedirs(media_dir_parent, exist_ok=True)

        success = render_manim_scenes(
            code_md_path=code_md_path,
            final_manim_output_media_dir=media_dir_target,
            project_root_path=project_root,
            cli_logger=logger # Pass the EUI CLI's logger instance
        )
        if success:
            logger.info(f"Manim rendering process completed. Output media should be in {media_dir_target}")
            if not os.path.exists(media_dir_target) or not any(os.scandir(media_dir_target)):
                logger.warning(f"Manim rendering reported success, but the output directory {media_dir_target} is empty or was not created.")
                # This could be a soft failure depending on expectations.
            return True
        else:
            logger.error(f"Manim rendering process failed or encountered errors. See logs and 'render_manim_errors.md'. Input: {code_md_path}")
            return False
    except Exception as e: # This was logger.error, changed to logger.exception
        logger.exception(f"An unexpected error occurred during Manim video rendering: {e}")
        return False

def run_create_final_video(script_path: str, audio_input_dir_param: str, manim_scenes_input_dir_param: str, final_video_path: str) -> bool:
    logger.info(f"Starting final video creation. Script: '{script_path}', Audio: '{audio_input_dir_param}', Manim scenes: '{manim_scenes_input_dir_param}' -> Video: '{final_video_path}'")
    try:
        if not os.path.exists(script_path):
            logger.error(f"Input script {script_path} not found.")
            return False
        # It's okay if audio/video dirs don't exist yet, tool should handle it.
        # But warn if they are unexpectedly empty if they DO exist.
        if os.path.exists(audio_input_dir_param) and not os.listdir(audio_input_dir_param): # Check if dir is empty
            logger.warning(f"Audio input directory {audio_input_dir_param} exists but is empty.")
        if os.path.exists(manim_scenes_input_dir_param) and not os.listdir(manim_scenes_input_dir_param): # Check if dir is empty
            logger.warning(f"Manim scenes input directory {manim_scenes_input_dir_param} exists but is empty.")

        create_video_from_script(
            logger=logger,
            script_filepath=os.path.abspath(script_path),
            audio_input_dir=os.path.abspath(audio_input_dir_param),
            manim_scenes_input_dir=os.path.abspath(manim_scenes_input_dir_param),
            output_filepath=os.path.abspath(final_video_path)
        )
        if os.path.exists(final_video_path):
            logger.info(f"Final video created successfully at {final_video_path}")
            return True
        else:
            logger.error(f"Final video file {final_video_path} was not found after creation attempt. Video tool may have failed.")
            return False
    except Exception as e:
        logger.exception(f"An unexpected error occurred during final video creation: {e}")
        return False

def run_all_pipeline(topic: str, output_dir_base: str) -> bool: # Added return type
    logger.info(f"Starting full pipeline for topic: '{topic}'. Output base directory: {output_dir_base}")
    try:
        os.makedirs(output_dir_base, exist_ok=True)

        user_script_json_output_path = os.path.join(output_dir_base, "script.json")
        user_code_md_output_path = os.path.join(output_dir_base, "code.md")
        user_audio_output_dir = os.path.join(output_dir_base, "audio_files")
        user_manim_media_output_dir = os.path.join(output_dir_base, "manim_media") # This is where render_manim_scenes saves CLASSNAME.mp4 files
        final_video_filename = f"{topic.replace(' ', '_').replace('-', '_').lower()}_final.mp4"
        user_final_video_output_path = os.path.join(output_dir_base, final_video_filename)

        logger.info("--- Step 1: Generating Script ---")
        if not run_generate_script(topic, user_script_json_output_path):
            logger.error("Script generation failed. Aborting pipeline.")
            return False

        logger.info("--- Step 2: Generating Manim Code ---")
        if not run_generate_manim_code(user_script_json_output_path, user_code_md_output_path):
            logger.error("Manim code generation failed. Aborting pipeline.")
            return False

        logger.info("--- Step 3: Generating Audio ---")
        # Audio generation is considered non-critical for now; pipeline continues with a warning.
        if not run_generate_audio(user_script_json_output_path, user_audio_output_dir):
            logger.warning(f"Audio generation step failed or produced no output. Output may be missing in {user_audio_output_dir}. Continuing pipeline.")
        elif not os.listdir(user_audio_output_dir):
            logger.warning(f"Audio generation step completed, but the output directory {user_audio_output_dir} is empty. Final video may lack audio.")
        else:
            logger.info(f"Audio files successfully generated in {user_audio_output_dir}")

        logger.info("--- Step 4: Rendering Manim Video Scenes ---")
        # Manim rendering is also considered non-critical for now if individual scenes fail.
        # render_manim_scenes returns True if the process ran, False for setup errors.
        # Individual scene errors are logged by render_manim_scenes itself.
        if not run_render_video(user_code_md_output_path, user_manim_media_output_dir):
            logger.warning(f"Manim rendering step reported issues (e.g. setup error, or all scenes failed). Output may be incomplete in {user_manim_media_output_dir}. Continuing pipeline.")
        elif not os.path.exists(user_manim_media_output_dir) or not os.listdir(user_manim_media_output_dir):
             logger.warning(f"Manim rendering step completed, but the output directory {user_manim_media_output_dir} is empty. Final video may lack Manim scenes.")
        else:
            logger.info(f"Manim scenes successfully rendered to {user_manim_media_output_dir}")

        logger.info("--- Step 5: Preparing Manim Videos for Final Stitching ---")
        temp_flat_manim_dir = os.path.join(output_dir_base, "temp_flat_manim_for_stitching")
        if os.path.exists(temp_flat_manim_dir):
            shutil.rmtree(temp_flat_manim_dir)
        os.makedirs(temp_flat_manim_dir, exist_ok=True)

        manim_prep_ok = True
        try:
            with open(user_script_json_output_path, 'r', encoding='utf-8') as f:
                script_data = json.load(f)

            manim_code_blocks = []
            if os.path.exists(user_code_md_output_path):
                with open(user_code_md_output_path, 'r', encoding='utf-8') as f_code:
                    content = f_code.read()
                from src.tools.render_manim_tool import find_scene_name # Assumes src.tools.render_manim_tool is in sys.path
                code_pattern = r"```(?:python)?\s*\n(.*?)\n```"
                manim_code_blocks = re.findall(code_pattern, content, re.DOTALL)
            else:
                logger.error(f"Manim code file {user_code_md_output_path} not found. Cannot map Manim class names for video stitching.")
                manim_prep_ok = False

            if manim_prep_ok and len(manim_code_blocks) != len(script_data):
                logger.warning(f"Mismatch: {len(script_data)} scenes in script, {len(manim_code_blocks)} Manim code blocks found. Scene mapping may be affected.")

            if manim_prep_ok:
                for idx, scene_item in enumerate(script_data):
                    scene_number = scene_item.get("scene_number", idx + 1)
                    manim_class_name = None
                    if idx < len(manim_code_blocks):
                        manim_class_name = find_scene_name(manim_code_blocks[idx])

                    if not manim_class_name:
                        logger.warning(f"Could not find Manim class name for scene {scene_number} in {user_code_md_output_path}. Skipping video copy for this scene.")
                        continue

                    src_video_path = os.path.join(user_manim_media_output_dir, f"{manim_class_name}.mp4")
                    dest_video_path = os.path.join(temp_flat_manim_dir, f"{scene_number}.mp4")

                    if os.path.exists(src_video_path):
                        shutil.copy(src_video_path, dest_video_path)
                        logger.debug(f"Copied Manim video for scene {scene_number} ({manim_class_name}.mp4) to {dest_video_path}")
                    else:
                        logger.warning(f"Manim video file {src_video_path} (for scene {scene_number}, class {manim_class_name}) not found. It will be missing from the final video.")

        except ImportError:
            logger.exception("Failed to import 'find_scene_name' for Manim video preparation. This is a critical setup error.")
            manim_prep_ok = False
        except Exception as e:
            logger.exception(f"An unexpected error occurred while preparing Manim videos for stitching: {e}")
            manim_prep_ok = False

        if not manim_prep_ok:
            logger.error("Due to critical errors in Manim video preparation, cannot proceed to final video stitching. Aborting.")
            if os.path.exists(temp_flat_manim_dir): shutil.rmtree(temp_flat_manim_dir)
            return False

        if not os.listdir(temp_flat_manim_dir) and len(script_data) > 0:
             logger.warning(f"Flattened Manim scenes directory ({temp_flat_manim_dir}) is empty. The final video might not contain any Manim scenes.")


        logger.info("--- Step 6: Creating Final Stitched Video ---")
        if not run_create_final_video(
            script_path=user_script_json_output_path,
            audio_input_dir_param=user_audio_output_dir,
            manim_scenes_input_dir_param=temp_flat_manim_dir,
            final_video_path=user_final_video_output_path
        ):
            logger.error("Final video stitching failed. Pipeline did not complete successfully.")
            if os.path.exists(temp_flat_manim_dir): shutil.rmtree(temp_flat_manim_dir) # Clean up temp dir
            return False

        logger.info(f"Final video successfully created at {user_final_video_output_path}")
        if os.path.exists(temp_flat_manim_dir): shutil.rmtree(temp_flat_manim_dir)

        logger.info(f"--- Full pipeline successfully finished for topic: '{topic}' ---")
        logger.info(f"All outputs are in: {output_dir_base}")
        return True

    except Exception as e: # Catch-all for the entire pipeline
        logger.exception(f"A critical unexpected error occurred in the 'all' pipeline: {e}")
        return False

def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Eui CLI tool for video creation pipeline.")
    subparsers = parser.add_subparsers(dest="command", help="Available commands", required=True)

    # Default paths, project_root should be defined globally
    default_output_base = os.path.join(project_root, "output") # General base for single command outputs
    default_script_output = os.path.join(default_output_base, "script.json")
    default_manim_code_output = os.path.join(default_output_base, "code.md")
    default_audio_output_dir = os.path.join(default_output_base, "audio_files")
    default_manim_media_dir = os.path.join(default_output_base, "manim_media_output")
    default_final_video_output = os.path.join(default_output_base, "final_video.mp4")
    default_pipeline_output_dir = os.path.join(project_root, "output", "full_pipeline_run")


    gs_parser = subparsers.add_parser("generate-script", help="Generate script JSON from a topic.")
    gs_parser.add_argument("--topic", required=True, help="Video topic.")
    gs_parser.add_argument("--output", default=default_script_output, help=f"Script JSON output path (default: {default_script_output}).")
    gs_parser.set_defaults(func=lambda args: run_generate_script(args.topic, args.output))

    gmc_parser = subparsers.add_parser("generate-manim-code", help="Generate Manim code from script JSON.")
    gmc_parser.add_argument("--script", default=default_script_output, help=f"Input script JSON path (default: {default_script_output}).")
    gmc_parser.add_argument("--output", default=default_manim_code_output, help=f"Manim code Markdown output path (default: {default_manim_code_output}).")
    gmc_parser.set_defaults(func=lambda args: run_generate_manim_code(args.script, args.output))

    ga_parser = subparsers.add_parser("generate-audio", help="Generate audio from script JSON.")
    ga_parser.add_argument("--script", default=default_script_output, help=f"Input script JSON path (default: {default_script_output}).")
    ga_parser.add_argument("--output_dir", default=default_audio_output_dir, help=f"Output directory for audio files (default: {default_audio_output_dir}).")
    ga_parser.set_defaults(func=lambda args: run_generate_audio(args.script, args.output_dir))

    rv_parser = subparsers.add_parser("render-video", help="Render Manim videos from code.")
    rv_parser.add_argument("--code", default=default_manim_code_output, help=f"Input Manim code Markdown path (default: {default_manim_code_output}).")
    rv_parser.add_argument("--media_dir", default=default_manim_media_dir, help=f"Output directory for rendered Manim media (default: {default_manim_media_dir}).")
    rv_parser.set_defaults(func=lambda args: run_render_video(args.code, args.media_dir))

    cfv_parser = subparsers.add_parser("create-final-video", help="Create final video from rendered scenes and audio.")
    cfv_parser.add_argument("--script", default=default_script_output, help=f"Input script JSON path (default: {default_script_output}).")
    cfv_parser.add_argument("--audio_input_dir", default=default_audio_output_dir, help=f"Directory containing numbered audio files (e.g., 1.mp3) (default: {default_audio_output_dir}).")
    cfv_parser.add_argument("--manim_input_dir", default=default_manim_media_dir, help=f"Directory containing **numbered** Manim video scene files (e.g., 1.mp4, 2.mp4) ready for stitching. User must prepare this structure. (default: {default_manim_media_dir}).")
    cfv_parser.add_argument("--output", default=default_final_video_output, help=f"Final video output path (default: {default_final_video_output}).")
    cfv_parser.set_defaults(func=lambda args: run_create_final_video(args.script, args.audio_input_dir, args.manim_input_dir, args.output))

    all_parser = subparsers.add_parser("all", help="Run the full video generation pipeline.")
    all_parser.add_argument("--topic", required=True, help="Video topic.")
    all_parser.add_argument("--output_dir", default=default_pipeline_output_dir, help=f"Base directory for all pipeline outputs (default: {default_pipeline_output_dir}).")
    all_parser.set_defaults(func=lambda args: run_all_pipeline(args.topic, args.output_dir))

    args = parser.parse_args()

    # Ensure GOOGLE_API_KEY is loaded if any command needs it
    # This check should ideally be inside the functions that directly use the API key.
    # For script_agent and manim_agent, they load dotenv themselves or expect it.
    # For this CLI, we ensure it's loaded once.
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key and (args.command in ["generate-script", "generate-manim-code", "all"]):
        logger.warning("GOOGLE_API_KEY not found in environment variables or .env file.")
        # The agents themselves might still find it if .env is in project_root and they call load_dotenv().
        # If not, they will fail. We'll let them handle the specific error.

    logger.info(f"Executing EUI CLI command: '{args.command}' with args: {vars(args)}")

    success = False
    try:
        # Each run_... function is expected to return True for success, False for failure.
        # They should also do their own specific error logging.
        # run_all_pipeline will return True only if all critical steps succeeded.
        success = args.func(args)
    except Exception as e:
        logger.exception(f"An unexpected error/exception occurred at the top level of command '{args.command}': {e}")
        success = False # Ensure sys.exit(1) is called

    if not success:
        logger.error(f"Command '{args.command}' ultimately failed.")
        sys.exit(1)
    else:
        logger.info(f"Command '{args.command}' completed successfully.")

if __name__ == "__main__":
    main()
