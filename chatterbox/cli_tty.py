import torchaudio as ta
import torch
from chatterbox.tts import ChatterboxTTS
import argparse
import sys
import os

def main():
    parser = argparse.ArgumentParser(description="Generate audio from text using ChatterboxTTS.")
    parser.add_argument("input_text", type=str, help="The text to synthesize.")
    parser.add_argument("output_path", type=str, help="The file path to save the generated audio.")
    # ...existing code...
    args = parser.parse_args()

    # Automatically detect the best available device
    if torch.cuda.is_available():
        device = "cuda"
    elif torch.backends.mps.is_available(): # For Apple Silicon
        device = "mps"
    else:
        device = "cpu"

    print(f"Using device: {device}")
    try:
        target_voice = os.path.join(os.getcwd(), "target.mp3")
    except Exception as e:
        target_voice = None

    try:
        model = ChatterboxTTS.from_pretrained(device=device)
    except Exception as e:
        print(f"Error loading model: {e}")
        sys.exit(1)

    text_to_synthesize = args.input_text
    output_file_path = args.output_path

    if not output_file_path:
        print("Error: Output file path must be provided.")
        sys.exit(1)

    try:
        print(f"Generating audio for: \"{text_to_synthesize}\"")
        if target_voice:
            wav = model.generate(text_to_synthesize, audio_prompt_path=target_voice, cfg_weight=.8, exaggeration=.5)
        else:
            wav = model.generate(text_to_synthesize, cfg_weight=.8, exaggeration=.5)
        ta.save(output_file_path, wav, model.sr)
        print(f"Audio saved to {output_file_path}")
    except Exception as e:
        print(f"Error during audio generation or saving: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()