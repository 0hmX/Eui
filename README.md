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

## Using the Agents and Tools

The primary workflow involves running the agents sequentially. Ensure your `uv`-managed virtual environment is activated and you are in the root `Eui` directory.

### 1. Generate the Video Script (`script_agent.py`)

This agent takes a topic as input and generates a `script.json` file, which outlines the structure and content of your video.

*   **Purpose:** To convert a single topic idea into a structured, multi-scene script suitable for automated processing by subsequent tools.
*   **Input:** A string describing the video topic.
*   **Output:** A `script.json` file in the project root, containing an array of scene objects.

**How to Run:**
```bash
uv run python -m src.agents.script_agent "Your Video Topic Here"
```
For example:
```bash
uv run python -m src.agents.script_agent "The Basics of Quantum Entanglement"
```
You can also specify an output file path:
```bash
uv run python -m src.agents.script_agent "My Topic" --output my_custom_script.json
```
This will create `script.json` (or your specified output file).

### 2. Generate Audio Files (`audio_tool.py`)

This tool reads the `script.json` file and generates an audio file for the "speech" part of each scene using the Chatterbox TTS.

*   **Purpose:** To convert the textual narration from `script.json` into audible speech.
*   **Input:** `script.json` (by default, from the project root).
*   **Output:** Audio files (e.g., `1.mp3`, `2.mp3`, etc.) in the `out/audio/` directory.

**How to Run:**
The `audio_tool.py` script is typically run directly. It expects `script.json` to be present in the root directory.
```bash
uv run python -m src.tools.audio_tool
```
It will iterate through `script.json`, find the `speech` field for each item, and call the `audo_generator_tool.py` (which uses Chatterbox) to create the audio files.

### 3. Generate Manim Animation Code (`manim_agent.py`)

This agent processes the `script.json` file, focusing on the "animation-description" for each scene, and generates Manim Python scripts.

*   **Purpose:** To translate textual descriptions of animations into executable Manim code.
*   **Input:** `script.json` (implicitly, by reading it).
*   **Output:** A `code.md` file in the `out/` directory, containing Manim Python code snippets for each scene. These snippets are intended to be runnable Manim scenes.

**How to Run:**
```bash
uv run python -m src.agents.manim_agent
```
This agent will read `script.json`, and for each item, it will use the `animation-description` to prompt an LLM (Gemini) to generate Manim code. The generated code (after type-checking attempts) is saved to `out/code.md`.

### 4. Render Manim Animations (`render_manim_tool.py`)

This tool takes the Manim Python code generated by `manim_agent.py` (from `out/code.md`) and renders each scene into a video file.

*   **Purpose:** To convert the Manim Python scripts into actual video animations.
*   **Input:** `out/code.md` (containing Manim scripts).
*   **Output:** Video files (e.g., `scene_1.mp4`, `scene_2.mp4`, etc.) in the `out/video/` directory.

**How to Run:**
```bash
uv run python -m src.tools.render_manim_tool
```
This script will parse `out/code.md`, extract each Manim scene code, save it as a temporary Python file, and then use Manim to render it.

### 5. (Future/Manual) Combine Audio and Video
After generating audio and video segments for each scene, you would typically combine them.
- For each scene `i`: Combine `out/audio/<i>.mp3` with `out/video/scene_<i>.mp4`.
- Concatenate all combined scenes into the final video.
This step might require a video editing tool like `ffmpeg` or a custom script.

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
- **`ImportError: attempted relative import with no known parent package`**: This usually means you are running a script directly from within a subdirectory (e.g., `python src/agents/script_agent.py`) instead of as a module from the project root. Use `uv run python -m src.agents.script_agent ...` from the `Eui` root directory.
- **`uv: command not found`**: Ensure `uv` is installed and in your system's PATH. Refer to the official `uv` installation guide.
- **Chatterbox errors**: Refer to the `chatterbox/README.md` and ensure all its dependencies and any required models are correctly set up.
