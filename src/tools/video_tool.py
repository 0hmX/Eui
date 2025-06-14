import json
import os
import glob
import tempfile
import shutil
import ffmpeg
import logging # Added
import sys # Added

# Adjust sys.path to find custom_logging
# This assumes the script is in Eui/src/tools and custom_logging.py is in Eui/src/utils
_CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
_SRC_DIR = os.path.dirname(_CURRENT_FILE_DIR)
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from utils.custom_logging import setup_custom_logging, log_node_ctx # Added

def get_media_duration(logger: logging.Logger, media_path: str) -> float | None:
    try:
        logger.debug(f"Probing: {media_path}")
        probe = ffmpeg.probe(media_path)
        duration_str = probe.get('format', {}).get('duration')
        if duration_str is not None:
            return float(duration_str)
        else:
            logger.error(f"Duration not found in ffprobe output for {media_path}")
            return None
    except ffmpeg.Error as e:
        logger.error(f"Error probing {media_path}:")
        logger.error(f"FFmpeg STDERR: {e.stderr.decode('utf8') if e.stderr else 'N/A'}")
        return None
    except (KeyError, ValueError, TypeError) as e:
        logger.error(f"Could not parse duration from ffprobe output for {media_path}: {e}")
        return None

def create_video_from_script(
    logger: logging.Logger,
    script_filename="script.json",
    output_filename="final_video.mp4",
    crf=23,
    enable_speed_up: bool = False,
    target_duration_minutes: float = 1.0
):
    with log_node_ctx(logger, "Video Creation Process"):
        script_file_path = os.path.join(os.getcwd(), script_filename)
        audio_base_dir = os.path.join(os.getcwd(), "out", "audio")
        video_base_dir = os.path.join(os.getcwd(), "media", "videos")
        
        temp_dir: str | None = None # Ensure temp_dir is defined for finally block

        try:
            temp_dir = tempfile.mkdtemp(prefix="video_processing_")
            logger.info(f"Created temporary directory: {temp_dir}")

            if not os.path.exists(script_file_path):
                logger.error(f"Script file not found at {script_file_path}")
                return

            try:
                with open(script_file_path, 'r', encoding='utf-8') as f:
                    script_items = json.load(f)
            except Exception as e:
                logger.error(f"Error reading or parsing script file {script_file_path}: {e}", exc_info=True)
                return

            if not script_items:
                logger.info("No items found in script.json. Exiting.")
                return

            processed_segment_files = []

            with log_node_ctx(logger, "Processing Video Segments"):
                for i, item in enumerate(script_items):
                    with log_node_ctx(logger, f"Segment {i+1}/{len(script_items)}"):
                        audio_file_path = os.path.join(audio_base_dir, f"{i+1}.mp3")
                        video_segment_folder_name = item.get("scene_name", f"temp_animation_scene_{i}")
                        video_folder_path = os.path.join(video_base_dir, video_segment_folder_name, "1920p60")

                        if not os.path.exists(audio_file_path):
                            logger.warning(f"Audio file not found for segment {i+1} at {audio_file_path}. Skipping.")
                            continue

                        video_files = glob.glob(os.path.join(video_folder_path, "*.mp4"))
                        if not video_files:
                            logger.warning(f"No MP4 video file found for segment {i+1} in {video_folder_path}. Skipping.")
                            logger.debug(f"Searched for video files in: {video_folder_path}")
                            fallback_video_path = os.path.join(video_base_dir, f"{video_segment_folder_name}.mp4")
                            if os.path.exists(fallback_video_path):
                                video_files = [fallback_video_path]
                                logger.info(f"Found fallback video: {fallback_video_path}")
                            else:
                                continue
                        
                        video_file_path = video_files[0]

                        audio_duration = get_media_duration(logger, audio_file_path)
                        video_duration = get_media_duration(logger, video_file_path)

                        if audio_duration is None or video_duration is None or audio_duration <= 0 or video_duration <= 0:
                            logger.warning(f"Could not get valid durations for segment {i+1} (Audio: {audio_duration}, Video: {video_duration}). Skipping.")
                            continue

                        final_segment_filename = f"final_segment_{i}.mp4"
                        final_segment_path = os.path.join(temp_dir, final_segment_filename)

                        logger.info(f"Video: {video_file_path} ({video_duration:.2f}s), Audio: {audio_file_path} ({audio_duration:.2f}s)")
                        logger.info(f"Stretching video to match audio duration ({audio_duration:.2f}s) and combining...")
                        
                        video_input = ffmpeg.input(video_file_path)
                        audio_input = ffmpeg.input(audio_file_path)
                        
                        video_stream = video_input.video
                        audio_stream = audio_input.audio

                        # Ensure durations are not None before division (already checked, but good for clarity)
                        if audio_duration == 0: # Avoid division by zero
                            logger.warning(f"Audio duration for segment {i+1} is zero. Skipping.")
                            continue
                        speed_factor = video_duration / audio_duration
                        
                        scaled_video = video_stream.filter('setpts', f'PTS/{speed_factor}')

                        try:
                            (
                                ffmpeg
                                .output(
                                    scaled_video,
                                    audio_stream,
                                    final_segment_path,
                                    **{
                                        'c:v': 'libx264', 'preset': 'medium', 'crf': crf,
                                        'c:a': 'aac', 'b:a': '192k', 'ar': '44100', 'shortest': None,
                                    }
                                )
                                .run(quiet=True, overwrite_output=True)
                            )
                            processed_segment_files.append(final_segment_path)
                            logger.info(f"Segment {i+1} processed successfully: {final_segment_path}")
                        except ffmpeg.Error as e:
                            logger.error(f"Error processing segment {i+1}:")
                            logger.error(f"FFmpeg STDERR: {e.stderr.decode('utf8') if e.stderr else 'N/A'}")
                            continue

            if not processed_segment_files:
                logger.warning("No segments were successfully processed. Final video cannot be created.")
                return

            with log_node_ctx(logger, "Concatenating Segments"):
                logger.info("Concatenating all processed segments...")
                
                input_nodes = [ffmpeg.input(p) for p in processed_segment_files]
                interleaved_streams = []
                for node in input_nodes:
                    interleaved_streams.append(node.video)
                    interleaved_streams.append(node.audio)

                concatenated_node = ffmpeg.concat(*interleaved_streams, v=1, a=1).node
                output_video_stream = concatenated_node[0]
                output_audio_stream = concatenated_node[1]
                
                concatenated_video_path = os.path.join(temp_dir, "concatenated_video.mp4")

                try:
                    (
                        ffmpeg
                        .output(
                            output_video_stream, output_audio_stream, concatenated_video_path,
                            **{'c:v': 'libx264', 'crf': crf, 'c:a': 'aac', 'b:a': '192k', 'ar': '44100', 'ac': 2}
                        )
                        .run(quiet=True, overwrite_output=True)
                    )
                    logger.info("Concatenation successful.")
                except ffmpeg.Error as e:
                    logger.error("Failed to concatenate video segments. Exiting.")
                    logger.error(f"FFmpeg STDERR: {e.stderr.decode('utf8') if e.stderr else 'N/A'}")
                    return

            total_duration_seconds = get_media_duration(logger, concatenated_video_path)
            if total_duration_seconds is None:
                logger.error("Failed to get duration of concatenated video. Exiting.")
                return
                
            logger.info(f"Total duration of stitched video: {total_duration_seconds:.2f}s")
            
            final_video_source_path = concatenated_video_path
            output_file_abs_path = os.path.join(os.getcwd(), "out", output_filename)
            os.makedirs(os.path.dirname(output_file_abs_path), exist_ok=True)

            target_duration_seconds = target_duration_minutes * 60.0
            if enable_speed_up and total_duration_seconds > target_duration_seconds:
                with log_node_ctx(logger, "Applying Final Speed-up"):
                    logger.info(f"Total duration ({total_duration_seconds:.2f}s) exceeds target ({target_duration_seconds:.2f}s). Speeding up final video.")
                    if target_duration_seconds == 0: # Avoid division by zero
                        logger.error("Target duration for speed-up is zero. Cannot apply speed-up.")
                    else:
                        final_speed_factor = total_duration_seconds / target_duration_seconds
                        sped_up_final_video_path = os.path.join(temp_dir, f"final_sped_up_{output_filename}")
                        
                        try:
                            input_stream = ffmpeg.input(concatenated_video_path)
                            video_stream = input_stream.video.filter('setpts', f'PTS/{final_speed_factor}')
                            audio_stream = input_stream.audio.filter('atempo', final_speed_factor) # Ensure atempo can handle the factor
                            
                            (
                                ffmpeg.output(
                                    video_stream,
                                    audio_stream,
                                    sped_up_final_video_path,
                                    **{'c:v': 'libx264', 'preset': 'medium', 'crf': 22, 'c:a': 'aac', 'b:a': '192k'}
                                )
                                .run(quiet=True, overwrite_output=True)
                            )
                            final_video_source_path = sped_up_final_video_path
                            logger.info(f"Final video successfully sped up to fit {target_duration_minutes:.2f} minutes.")
                        except ffmpeg.Error as e: # Corrected except block
                            logger.error("Failed to speed up final video. Using original concatenated video instead.")
                            logger.error(f"FFmpeg STDERR: {e.stderr.decode('utf8') if e.stderr else 'N/A'}")
            elif enable_speed_up:
                logger.info(f"Speed-up enabled, but total duration ({total_duration_seconds:.2f}s) is already within target ({target_duration_seconds:.2f}s). No speed-up applied.")
            else:
                logger.info("Final speed-up is not enabled. Using original concatenated video duration.")

            logger.info(f"Copying final video to {output_file_abs_path}...")
            shutil.copyfile(final_video_source_path, output_file_abs_path)
            logger.info(f"✅ Successfully created video: {output_file_abs_path}")

        except Exception as e: # General exception handler for the main try block
            logger.critical(f"An unexpected error occurred in video creation: {e}", exc_info=True)
        finally: # This finally clause corresponds to the main try block
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                    logger.info(f"Cleaned up temporary directory: {temp_dir}")
                except Exception as e_clean:
                    logger.error(f"Error cleaning up temporary directory {temp_dir}: {e_clean}", exc_info=True)

if __name__ == "__main__":
    main_logger = setup_custom_logging(logger_name="VideoToolMain", level=logging.INFO)
    
    try:
        create_video_from_script(
            main_logger,
            output_filename="final_video.mp4",
            crf=23,
            enable_speed_up=False,
            target_duration_minutes=2.0
        )
    except Exception as e:
        main_logger.critical(f"Unhandled exception in __main__: {e}", exc_info=True)
        sys.exit(1)
    except KeyboardInterrupt:
        main_logger.warning("Script interrupted by user (Ctrl+C).")
        sys.exit(130)