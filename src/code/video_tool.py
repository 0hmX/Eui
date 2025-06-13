import json
import os
import glob
import tempfile
import shutil
import ffmpeg

def get_media_duration(media_path):
    try:
        print(f"Probing: {media_path}")
        probe = ffmpeg.probe(media_path)
        return float(probe['format']['duration'])
    except ffmpeg.Error as e:
        print(f"Error probing {media_path}:")
        print(f"STDERR: {e.stderr.decode('utf8')}")
        return None
    except (KeyError, ValueError) as e:
        print(f"Could not parse duration from ffprobe output for {media_path}: {e}")
        return None

def create_video_from_script(
    script_filename="script.json",
    output_filename="final_video.mp4",
    crf=23
):
    script_file_path = os.path.join(os.getcwd(), script_filename)
    audio_base_dir = os.path.join(os.getcwd(), "out", "audio")
    video_base_dir = os.path.join(os.getcwd(), "media", "videos")
    
    temp_dir = None

    try:
        temp_dir = tempfile.mkdtemp(prefix="video_processing_")
        print(f"Created temporary directory: {temp_dir}")

        if not os.path.exists(script_file_path):
            print(f"Error: Script file not found at {script_file_path}")
            return

        try:
            with open(script_file_path, 'r', encoding='utf-8') as f:
                script_items = json.load(f)
        except Exception as e:
            print(f"Error reading or parsing script file {script_file_path}: {e}")
            return

        if not script_items:
            print("No items found in script.json. Exiting.")
            return

        processed_segment_files = []

        for i, item in enumerate(script_items):
            print(f"\nProcessing segment {i+1}/{len(script_items)}...")

            audio_file_path = os.path.join(audio_base_dir, f"{i+1}.mp3")
            video_segment_folder_name = f"temp_animation_scene_{i}"
            video_folder_path = os.path.join(video_base_dir, video_segment_folder_name, "1920p60")

            if not os.path.exists(audio_file_path):
                print(f"Warning: Audio file not found for segment {i+1} at {audio_file_path}. Skipping.")
                continue

            video_files = glob.glob(os.path.join(video_folder_path, "*.mp4"))
            if not video_files:
                print(f"Warning: No MP4 video file found for segment {i+1} in {video_folder_path}. Skipping.")
                continue
            video_file_path = video_files[0]

            audio_duration = get_media_duration(audio_file_path)
            video_duration = get_media_duration(video_file_path)

            if not all([audio_duration, video_duration]) or audio_duration <= 0 or video_duration <= 0: # type: ignore
                print(f"Warning: Could not get valid durations for segment {i+1}. Skipping.")
                continue

            final_segment_filename = f"final_segment_{i}.mp4"
            final_segment_path = os.path.join(temp_dir, final_segment_filename)

            print(f"  Stretching video to match audio duration ({audio_duration:.2f}s) and combining...")
            
            video_input = ffmpeg.input(video_file_path)
            audio_input = ffmpeg.input(audio_file_path)
            
            video_stream = video_input.video
            audio_stream = audio_input.audio

            speed_factor = video_duration / audio_duration # type: ignore
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
                print(f"  Segment {i+1} processed successfully: {final_segment_path}")
            except ffmpeg.Error as e:
                print(f"Error processing segment {i+1}:")
                print(f"FFmpeg STDERR: {e.stderr.decode('utf8')}")
                continue

        if not processed_segment_files:
            print("No segments were successfully processed. Final video cannot be created.")
            return

        print("\nConcatenating all processed segments...")
        
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
            print("Concatenation successful.")
        except ffmpeg.Error as e:
            print("Failed to concatenate video segments. Exiting.")
            print(f"FFmpeg STDERR: {e.stderr.decode('utf8')}")
            return

        total_duration = get_media_duration(concatenated_video_path)
        if total_duration is None:
            print("Failed to get duration of concatenated video. Exiting.")
            return
            
        print(f"Total duration of stitched video: {total_duration:.2f}s")
        
        final_video_source_path = concatenated_video_path
        output_file_abs_path = os.path.join(os.getcwd(), "out", output_filename)
        os.makedirs(os.path.dirname(output_file_abs_path), exist_ok=True)

        if total_duration > 60.0:
            print("Total duration exceeds 60 seconds. Speeding up final video to fit 60s.")
            final_speed_factor = total_duration / 60.0
            
            sped_up_final_video_path = os.path.join(temp_dir, f"final_sped_up_{output_filename}")
            
            try:
                input_stream = ffmpeg.input(concatenated_video_path)
                video_stream = input_stream.video.filter('setpts', f'PTS/{final_speed_factor}')
                audio_stream = input_stream.audio.filter('atempo', final_speed_factor)
                
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
                print("Final video successfully sped up.")
            except ffmpeg.Error as e:
                print("Failed to speed up final video. Using original concatenated video instead.")
                print(f"FFmpeg STDERR: {e.stderr.decode('utf8')}")
        
        print(f"\nCopying final video to {output_file_abs_path}...")
        shutil.copyfile(final_video_source_path, output_file_abs_path)
        print(f"✅ Successfully created video: {output_file_abs_path}")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                print(f"Cleaned up temporary directory: {temp_dir}")
            except Exception as e_clean:
                print(f"Error cleaning up temporary directory {temp_dir}: {e_clean}")

if __name__ == "__main__":
    create_video_from_script(
        output_filename="final_video.mp4",
        crf=23 
    )