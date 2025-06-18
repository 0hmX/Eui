# Eui: The Automated Content Framework

## Overview
Eui is an automated content creation framework designed to streamline the production of video content, particularly for platforms like YouTube Shorts. It leverages the Manim library for generating mathematical and technical animations and the Chatterbox TTS model for voiceovers. This project is actively used to automate content for the [TheAnkanOfficial YouTube channel](https://www.youtube.com/@TheAnkanOfficial).

The core idea is to take a simple topic, generate a detailed script, convert script narrations into audio, generate corresponding animations for each part of the script, and finally combine these into a video.

**Example Videos Created with Eui:**
- [Short 1](https://youtube.com/shorts/b19_st7Rr8U)
- [Short 2](https://www.youtube.com/shorts/F9I2rSiC1Z0)

## Core Components & Workflow
The framework operates through a series of agents and tools:

1.  **Script Generation (`script_agent.py`):** Takes a high-level topic and generates a detailed `script.json` file. This JSON file breaks down the video into scenes, each with descriptions for music, speech, animation, and duration.
2.  **Audio Generation (`audio_tool.py`):** Processes the `script.json` file, using the "speech" text from each scene to generate corresponding audio files (e.g., `.mp3`) using the Chatterbox TTS.
3.  **Manim Code Generation (`manim_agent.py`):** Reads the `script.json` (specifically the "animation-description" for each scene) and generates Python scripts for Manim. These scripts, when run, produce the visual animations.
4.  **Manim Rendering (`render_manim_tool.py`):** Takes the generated Manim Python scripts and renders them into video segments.
5.  **Video Assembly (Future/Manual):** Combines the audio and video segments for each scene, and then concatenates these scenes into a final video. (This part might be manual or handled by a separate tool/script not detailed here).

## How to Install

1.  **Clone the Repository (with Submodules):**
    Eui uses submodules (e.g., for Chatterbox). Clone it recursively:
    ```bash
    git clone --recursive <your-repository-url>
    cd Eui
    ```
    If you've already cloned without `--recursive`, you can initialize and update submodules:
    ```bash
    git submodule update --init --recursive
    ```

2.  **Install `uv`:**
    This project uses `uv` for Python packaging and workflow management. If you don't have `uv` installed, please follow the official installation instructions at [https://github.com/astral-sh/uv#installation](https://github.com/astral-sh/uv#installation). Common methods include using `curl` (macOS/Linux) or `Invoke-WebRequest` (Windows).

3.  **Set up Python Environment & Install Dependencies:**
    Ensure you have Python installed (refer to [.python-version](.python-version) for the specific version). `uv` can create and manage virtual environments.
    From the root of the `Eui` project directory:
    ```bash
    # Create a virtual environment named .venv using the Python version from .python-version (if present) or a discoverable Python
    uv venv
    # Install project dependencies from pyproject.toml and uv.lock
    uv sync
    ```

4.  **Set up Chatterbox TTS:**
    The [chatterbox/](chatterbox/) directory contains the Chatterbox TTS component. Navigate to it and install its specific dependencies using `uv`. Refer to [chatterbox/README.md](chatterbox/README.md) for any detailed instructions.
    ```bash
    cd chatterbox
    # Ensure the main project's virtual environment is active or create/sync one here if it's managed separately
    uv sync # This will install dependencies defined in chatterbox/pyproject.toml
    cd ..
    ```

5.  **Environment Variables:**
    The agents require a `GOOGLE_API_KEY` for accessing Google's Generative AI models. Create a `.env` file in the root of the `Eui` project directory:
    ```
    # .env
    GOOGLE_API_KEY="your_google_api_key_here"
    ```
    Replace `"your_google_api_key_here"` with your actual API key.

## Workflow Components (Internal Details)

The Eui framework is composed of several core Python scripts located in the `src/` directory. While the recommended way to use the framework is through the [Eui CLI Tool](#eui-cli-tool-bineuipy), understanding these components can be helpful for developers or for debugging. The CLI tool essentially orchestrates these components.

### 1. Script Generation (`src/agents/script_agent.py`)

*   **Purpose:** Takes a high-level topic and generates a detailed `script.json` file. This JSON file breaks down the video into scenes, each with descriptions for music, speech, animation, and duration.
*   **Input:** A string describing the video topic.
*   **Output:** A `script.json` file (by default), containing an array of scene objects.

### 2. Manim Code Generation (`src/agents/manim_agent.py`)

*   **Purpose:** Reads the `script.json` (specifically the "animation-description" for each scene) and generates Python scripts for Manim.
*   **Input:** A `script.json` file.
*   **Output:** A Markdown file (e.g., `code.md`) containing Manim Python code snippets for each scene.

### 3. Audio Generation (`src/tools/audio_tool.py` & `src/tools/audio_generator_tool.py`)

*   **Purpose:** `audio_tool.py` processes the `script.json` file, taking the "speech" text from each scene. It then calls `audio_generator_tool.py` (which uses Chatterbox TTS) to generate corresponding audio files.
*   **Input:** A `script.json` file.
*   **Output:** Numbered audio files (e.g., `1.mp3`, `2.mp3`, etc.) for each scene.

### 4. Manim Rendering (`src/tools/render_manim_tool.py`)

*   **Purpose:** Takes the generated Manim Python scripts (typically from a Markdown file) and renders them into video segments.
*   **Input:** A Markdown file containing Manim scripts.
*   **Output:** Video files for each rendered Manim scene.

### 5. Video Stitching (`src/tools/video_tool.py`)

*   **Purpose:** Combines the generated audio and Manim video segments for each scene, and then concatenates these scenes into a final video file.
*   **Input:** A `script.json` file, a directory of numbered audio files, and a directory of numbered Manim video files.
*   **Output:** A final MP4 video.

For detailed usage and to run these steps, please refer to the [Eui CLI Tool](#eui-cli-tool-bineuipy) documentation below.

## Eui CLI Tool (`bin/eui.py`)

The Eui CLI tool (`bin/eui.py`) provides a unified command-line interface to orchestrate the entire video creation workflow, from generating a script to rendering the final video. It simplifies the process by consolidating the individual steps described above.

### Setup

1.  **Project Dependencies**: Ensure you have followed the main project [Installation](#how-to-install) steps, particularly installing dependencies with `uv sync`. The CLI tool uses the same environment.
2.  **Environment Variables**: The CLI tool, especially commands involving content generation (like `generate-script`, `generate-manim-code`, and `all`), requires a `GOOGLE_API_KEY`. Make sure you have a `.env` file in the project root as described in the main installation instructions.

### Usage

The CLI tool is located at `bin/eui.py`. You can run it using:

```bash
python bin/eui.py <command> [options]
```

Or, if you make it executable (`chmod +x bin/eui.py`):

```bash
./bin/eui.py <command> [options]
```

To see all available commands and their general help:
```bash
python bin/eui.py --help
```
To see help for a specific command:
```bash
python bin/eui.py <command> --help
```

### Commands

#### `generate-script`
Generates a script JSON file from a given topic.

*   **Arguments:**
    *   `--topic <topic>`: (Required) The topic for the video.
    *   `--output <path>`: (Optional) Path to save the generated script JSON file. Defaults to `output/script.json`.
*   **Example:**
    ```bash
    python bin/eui.py generate-script --topic "The Science of Black Holes" --output my_project/black_holes_script.json
    ```

#### `generate-manim-code`
Generates Manim Python code (as Markdown) from a script JSON file.

*   **Arguments:**
    *   `--script <path>`: (Optional) Path to the input script JSON file. Defaults to `output/script.json`.
    *   `--output <path>`: (Optional) Path to save the generated Manim code Markdown file. Defaults to `output/code.md`.
*   **Example:**
    ```bash
    python bin/eui.py generate-manim-code --script my_project/black_holes_script.json --output my_project/manim_code.md
    ```

#### `generate-audio`
Generates audio files from the speech segments in a script JSON file.

*   **Arguments:**
    *   `--script <path>`: (Optional) Path to the input script JSON file. Defaults to `output/script.json`.
    *   `--output_dir <directory>`: (Optional) Directory to save the generated audio files (e.g., `1.mp3`, `2.mp3`). Defaults to `output/audio_files/`.
*   **Example:**
    ```bash
    python bin/eui.py generate-audio --script my_project/black_holes_script.json --output_dir my_project/audio_clips
    ```

#### `render-video`
Renders Manim video scenes from a Manim code Markdown file.

*   **Arguments:**
    *   `--code <path>`: (Optional) Path to the input Manim code Markdown file. Defaults to `output/code.md`.
    *   `--media_dir <directory>`: (Optional) Directory to save the rendered Manim media files (e.g., `SceneClassName.mp4`). Defaults to `output/manim_media_output/`.
*   **Example:**
    ```bash
    python bin/eui.py render-video --code my_project/manim_code.md --media_dir my_project/rendered_scenes
    ```

#### `create-final-video`
Creates the final video by stitching together audio and Manim video scenes based on a script JSON file.
**Note**: This command expects the `--manim_input_dir` to contain video files that are already numbered according to the script order (e.g., `1.mp4`, `2.mp4`). The `all` command handles this renaming automatically.

*   **Arguments:**
    *   `--script <path>`: (Optional) Path to the input script JSON file. Defaults to `output/script.json`.
    *   `--audio_input_dir <directory>`: (Optional) Directory containing numbered audio files (e.g., `1.mp3`). Defaults to `output/audio_files/`.
    *   `--manim_input_dir <directory>`: (Optional) Directory containing **numbered** Manim video scene files (e.g., `1.mp4`, `2.mp4`). Defaults to `output/manim_media_output/`.
    *   `--output <path>`: (Optional) Path to save the final combined video file. Defaults to `output/final_video.mp4`.
*   **Example:**
    ```bash
    python bin/eui.py create-final-video --script my_project/script.json --audio_input_dir my_project/audio_clips --manim_input_dir my_project/numbered_manim_scenes --output my_project/final_output_video.mp4
    ```

#### `all`
Runs the entire video generation pipeline: generates script, Manim code, audio, renders Manim scenes, and creates the final video.

*   **Arguments:**
    *   `--topic <topic>`: (Required) The topic for the video.
    *   `--output_dir <directory>`: (Optional) The base directory where all intermediate and final outputs (script, code, audio, media, final video) will be saved. Defaults to `output/full_pipeline_run/`.
*   **Example:**
    ```bash
    python bin/eui.py all --topic "The Wonders of the Cosmos" --output_dir video_projects/cosmos_show
    ```

## Project Structure
```
Eui/
├── .env                    # For API keys and environment variables (you create this)
├── .python-version         # Specifies Python version (used by uv venv)
├── .venv/                  # Virtual environment directory (managed by uv)
├── chatterbox/             # Chatterbox TTS submodule
│   └── pyproject.toml      # Chatterbox dependencies
├── out/                    # Output directory for generated files
│   ├── audio/              # Generated audio files (e.g., 1.mp3, 2.mp3)
│   ├── code.md             # Generated Manim Python code
│   └── video/              # Rendered Manim video scenes (e.g., scene_1.mp4)
├── prompts/                # Prompt templates for LLMs
│   ├── common_error.md
│   └── generate_video_prompt.md
├── src/
│   ├── agents/             # Core AI agent logic
│   │   ├── __init__.py
│   │   ├── manim_agent.py  # Generates Manim code from script descriptions
│   │   └── script_agent.py # Generates script.json from a topic
│   ├── tools/              # Utility scripts for processing
│   │   ├── __init__.py
│   │   ├── audio_tool.py   # Orchestrates TTS audio generation
│   │   ├── audo_generator_tool.py # CLI for Chatterbox TTS (called by audio_tool)
│   │   └── render_manim_tool.py # Renders Manim code into videos
│   └── utils/              # Shared utility functions
│       ├── __init__.py
│       └── custom_logging.py # Custom logging setup
├── .gitignore
├── env.sh                  # Example environment setup script
├── pyproject.toml          # Project metadata and dependencies for uv
├── README.md               # This file
├── script.json             # Example or generated video script
└── uv.lock                 # uv lock file for reproducible dependencies
```

## Contributing
Contributions to Eui are welcome! Please follow these general guidelines:

1.  **Fork the repository.**
2.  **Create a new branch** for your feature or bug fix (e.g., `git checkout -b feature/your-feature` or `bugfix/fix-something`).
3.  **Make your changes** and commit them with clear, descriptive messages.
4.  **Test your changes** thoroughly.
5.  **Push your branch** to your fork.
6.  **Open a Pull Request (PR)** against the main Eui repository, detailing your changes, why they are needed, and how you tested them.

## Troubleshooting
- **`ImportError: attempted relative import with no known parent package`**: If you encounter this while trying to run scripts from `src/` directly, it's because they are designed to be part of a package. The recommended way to use the project is via the `bin/eui.py` CLI tool from the project root.
- **`uv: command not found`**: Ensure `uv` is installed and in your system's PATH. Refer to the official `uv` installation guide.
- **Chatterbox errors**: Refer to the `chatterbox/README.md` and ensure all its dependencies and any required models are correctly set up.
