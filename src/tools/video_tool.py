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
    script_filepath: str, # Changed: absolute path
    audio_input_dir: str, # Changed: absolute path
    manim_scenes_input_dir: str, # Changed: absolute path to flat dir with scene videos
    output_filepath: str, # Changed: absolute path
    crf=23,
    enable_speed_up: bool = False,
    target_duration_minutes: float = 1.0
):
    with log_node_ctx(logger, "Video Creation Process"):
        # script_filepath is now absolute
        # audio_input_dir is now absolute
        # manim_scenes_input_dir is now absolute and expected to be flat
        # output_filepath is now absolute
        
        temp_dir: str | None = None

        try:
            temp_dir = tempfile.mkdtemp(prefix="video_processing_")
            logger.info(f"Created temporary directory: {temp_dir}")

            if not os.path.exists(script_filepath):
                logger.error(f"Script file not found at {script_filepath}")
                return

            try:
                with open(script_filepath, 'r', encoding='utf-8') as f:
                    script_items = json.load(f)
            except Exception as e:
                logger.error(f"Error reading or parsing script file {script_filepath}: {e}", exc_info=True)
                return

            if not script_items:
                logger.info("No items found in script.json. Exiting.")
                return

            processed_segment_files = []

            with log_node_ctx(logger, "Processing Video Segments"):
                for i, item in enumerate(script_items):
                    scene_number = item.get("scene_number", i + 1)
                    with log_node_ctx(logger, f"Segment for Scene {scene_number} ({i+1}/{len(script_items)})"):
                        # Audio files are named by scene_number (or index)
                        audio_file_path = os.path.join(audio_input_dir, f"{scene_number}.mp3")

                        # Video files: ASSUMPTION: Manim scenes are in manim_scenes_input_dir,
                        # named corresponding to scene_number from script.json (e.g., 1.mp4, 2.mp4)
                        # This part is crucial and relies on how run_all_pipeline prepares this directory.
                        # The 'scene_name' from script.json is the description, not Manim class name.
                        # We'll use scene_number as the primary key for video files.
                        video_file_name_candidate = f"{scene_number}.mp4"
                        video_file_path = os.path.join(manim_scenes_input_dir, video_file_name_candidate)

                        if not os.path.exists(audio_file_path):
                            logger.warning(f"Audio file not found for scene {scene_number} at {audio_file_path}. Skipping segment.")
                            continue

                        if not os.path.exists(video_file_path):
                            logger.warning(f"Video file not found for scene {scene_number} at {video_file_path}. Attempting fallback if applicable, else skipping.")
                            # Fallback: try to find ANY .mp4 file if only one exists (less robust)
                            # For now, strict check:
                            # TODO: More robust video finding if names don't align perfectly or if multiple videos per scene exist.
                            # Example: if manim output SceneClassName.mp4, and script.json has scene_number,
                            # a mapping or renaming step is needed BEFORE this tool.
                            continue
                        
                        audio_duration = get_media_duration(logger, audio_file_path)
                        video_duration = get_media_duration(logger, video_file_path)

                        if audio_duration is None or video_duration is None or audio_duration <= 0 or video_duration <= 0:
                            logger.warning(f"Could not get valid durations for scene {scene_number} (Audio: {audio_duration}, Video: {video_duration}). Skipping segment.")
                            continue

                        final_segment_filename = f"final_segment_{scene_number}.mp4" # Use scene_number for clarity
                        final_segment_path = os.path.join(temp_dir, final_segment_filename)

                        logger.info(f"Video (scene {scene_number}): {video_file_path} ({video_duration:.2f}s), Audio: {audio_file_path} ({audio_duration:.2f}s)")
                        logger.info(f"Processing video to match audio duration ({audio_duration:.2f}s) and combining...")
                        
                        video_input_stream = ffmpeg.input(video_file_path)
                        audio_input_stream = ffmpeg.input(audio_file_path)
                        
                        processed_video_stream = video_input_stream.video
                        processed_audio_stream = audio_input_stream.audio

                        # Stretch or cut video to match audio_duration
                        # Using setpts for stretching/compressing video
                        # Using atrim and asetpts for audio if needed, but audio is leading here.
                        # Video speed factor: if video is shorter, speed_factor < 1 (slow down). If longer, speed_factor > 1 (speed up).
                        if video_duration == 0: audio_duration = 1e-6 # Avoid division by zero for speed_factor, effectively making video very fast if it has no duration
                        video_speed_factor = video_duration / audio_duration

                        # Apply video speed change
                        # Note: setpts affects timestamp, not actual frame rate directly.
                        # Forcing frame rate with -r might be needed if issues with variable frame rate.
                        processed_video_stream = processed_video_stream.filter('setpts', f'PTS/{video_speed_factor}')
                        
                        # If audio is longer than video, the video is slowed down.
                        # If audio is shorter, video is sped up.
                        # The 'shortest' option is not used here because we explicitly want video to match audio length.

                        try:
                            (
                                ffmpeg
                                .output(
                                    processed_video_stream,
                                    processed_audio_stream, # Original audio stream
                                    final_segment_path,
                                    **{
                                        'c:v': 'libx264', 'preset': 'medium', 'crf': crf, 'r': 30, # Standard frame rate
                                        'c:a': 'aac', 'b:a': '192k', 'ar': '44100',
                                        't': audio_duration # Explicitly set duration of output to audio_duration
                                    }
                                )
                                .run(quiet=True, overwrite_output=True) # quiet=False for debugging
                            )
                            processed_segment_files.append(final_segment_path)
                            logger.info(f"Segment for scene {scene_number} processed successfully: {final_segment_path}")
                        except ffmpeg.Error as e:
                            logger.error(f"Error processing segment for scene {scene_number}:")
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
                return # output_filepath is an absolute path
                
            logger.info(f"Total duration of stitched video: {total_duration_seconds:.2f}s")
            
            final_video_source_path = concatenated_video_path
            # output_filepath is already absolute. Ensure parent directory exists.
            os.makedirs(os.path.dirname(output_filepath), exist_ok=True)

            target_duration_seconds = target_duration_minutes * 60.0
            if enable_speed_up and total_duration_seconds > target_duration_seconds:
                with log_node_ctx(logger, "Applying Final Speed-up"):
                    logger.info(f"Total duration ({total_duration_seconds:.2f}s) exceeds target ({target_duration_seconds:.2f}s). Speeding up final video.")
                    if target_duration_seconds == 0:
                        logger.error("Target duration for speed-up is zero. Cannot apply speed-up.")
                    else:
                        final_speed_factor = total_duration_seconds / target_duration_seconds
                        # Use a descriptive name for the sped-up temp file
                        base_output_filename = os.path.basename(output_filepath)
                        sped_up_final_video_path = os.path.join(temp_dir, f"sped_up_{base_output_filename}")
                        
                        try:
                            input_stream = ffmpeg.input(concatenated_video_path)
                            video_s = input_stream.video.filter('setpts', f'PTS/{final_speed_factor}')
                            # For audio speed up, atempo filter is limited (0.5 to 100.0).
                            # If factor is outside this, may need multiple atempo or rubberband.
                            # Simple approach: if factor is too large/small, cap it or warn.
                            # For now, assume factor is reasonable.
                            audio_s = input_stream.audio.filter('atempo', final_speed_factor)
                            
                            (
                                ffmpeg.output(
                                    video_s, audio_s, sped_up_final_video_path,
                                    **{'c:v': 'libx264', 'preset': 'medium', 'crf': 22, 'c:a': 'aac', 'b:a': '192k'}
                                )
                                .run(quiet=True, overwrite_output=True)
                            )
                            final_video_source_path = sped_up_final_video_path
                            logger.info(f"Final video successfully sped up to fit {target_duration_minutes:.2f} minutes. New temp path: {final_video_source_path}")
                        except ffmpeg.Error as e:
                            logger.error("Failed to speed up final video. Using original concatenated video instead.")
                            logger.error(f"FFmpeg STDERR: {e.stderr.decode('utf8') if e.stderr else 'N/A'}")
            elif enable_speed_up:
                logger.info(f"Speed-up enabled, but total duration ({total_duration_seconds:.2f}s) is already within target ({target_duration_seconds:.2f}s). No speed-up applied.")
            else:
                logger.info("Final speed-up is not enabled. Using original concatenated video duration.")

            logger.info(f"Copying final video to {output_filepath}...")
            shutil.copyfile(final_video_source_path, output_filepath)
            logger.info(f"✅ Successfully created video: {output_filepath}")

        except Exception as e:
            logger.critical(f"An unexpected error occurred in video creation: {e}", exc_info=True)
        finally:
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                    logger.info(f"Cleaned up temporary directory: {temp_dir}")
                except Exception as e_clean:
                    logger.error(f"Error cleaning up temporary directory {temp_dir}: {e_clean}", exc_info=True)