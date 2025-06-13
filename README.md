# Eui: The automated content framework

## Overview
Eui is an automated content creation framework designed to streamline the production of video content. It leverages the Manim library for generating mathematical animations and the Chatterbox TTS model for voiceovers, facilitating the creation of technical videos, such as YouTube Shorts. The system uses scripts (e.g., [script.json](script.json)) to define content, processes audio using tools like [src/code/audio_tool.py](src/code/audio_tool.py), and renders animations via Manim scripts managed by tools like [src/code/render_manim_tool.py](src/code/render_manim_tool.py).

## How to Install

1.  **Clone the Repository:**
    ```bash
    git clone <your-repository-url>
    cd Eui
    ```

2.  **Set up Python Environment:**
    Ensure you have Python installed (refer to [.python-version](.python-version) for the specific version). It is recommended to use a virtual environment:
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .\.venv\Scripts\activate
    ```
    If an environment setup script like [env.sh](env.sh) exists, source it:
    ```bash
    source env.sh
    ```

3.  **Install Dependencies with `uv`:**
    This project uses `uv` for dependency management, as indicated by [uv.lock](uv.lock) and [pyproject.toml](pyproject.toml).
    If you don't have `uv` installed, first install it:
    ```bash
    pip install uv
    ```
    Then, install project dependencies using `uv`:
    ```bash
    uv pip install .
    ```

4.  **Set up Chatterbox:**
    The [chatterbox/](chatterbox/) directory contains the Chatterbox TTS component. Navigate to it and install its dependencies using `uv`, referring to [chatterbox/README.md](chatterbox/README.md) for detailed instructions. This typically involves:
    ```bash
    cd chatterbox
    uv pip install .
    cd ..
    ```

## Contributing
Contributions to Eui are welcome! Please follow these general guidelines:

1.  **Fork the repository.**
2.  **Create a new branch** for your feature or bug fix (e.g., `git checkout -b feature/your-feature` or `bugfix/fix-something`).
3.  **Make your changes** and commit them with clear, descriptive messages.
4.  **Adhere to project standards.** This project uses Ruff for linting (indicated by the `.ruff_cache/` directory).
5.  **Push your branch** to your fork.
6.  **Open a Pull Request (PR)** against the main Eui repository, detailing your changes.