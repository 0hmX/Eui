# Eui Development Instructions

- Eui 2 is a TypeScript/Bun implementation developed alongside the legacy Python prototype.
- Use Bun exclusively for JavaScript/TypeScript dependency management, scripts, and tests.
- Keep the authored video format declarative and validate external input before compiling it.
- Treat generated narration as immutable, content-addressed build input. Visual-only edits must not regenerate audio.
- Use Manim as the sole animation renderer. Keep its Python runtime behind an adapter boundary.
- Keep Chatterbox isolated behind an audio-provider interface and a small Python worker. Tests must not download or execute the model.
- For tscircuit content, use the bundled tscircuit skill and generate visual assets with `tsci build` or `tsci snapshot`. Never invent or draw a PCB illustration unless the user explicitly asks for an illustration.
- Keep the visual tool set small: narration, captions, text, and verified media assets. Do not implement code-diff animation.
- Prefer deterministic tests with fixtures. Do not require network access, GPU access, API keys, or FFmpeg for unit tests.
- The `workflow/` directory contains the non-interactive Codex implementation workflow. Do not edit completion state under `.eui-workflow/`.
