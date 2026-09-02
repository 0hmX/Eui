# Stage 4: CLI, example project, and end-to-end build graph

Join the implemented packages into a usable local workflow.

Implement a TypeScript CLI with these commands:

- `eui validate <project>`
- `eui voice <project>`
- `eui preview <project>`
- `eui render <project>`
- `eui inspect <project>`
- `eui doctor`

Requirements:

- Commands are non-interactive by default and return meaningful exit codes.
- Add `--json` where machine-readable status is useful.
- Build stages form a resumable content-addressed graph: validate, audio, alignment, prepare, render, mux, captions, manifest.
- `inspect` explains resolved cues, durations, cache keys, and why a stage is stale without invoking models or rendering.
- Provide one compact vertical-video example featuring narration cues, captions, and an animated TypeScript code diff.
- Generate final artifact paths for MP4, narration WAV, SRT/VTT captions, and build manifest. External binaries may be adapters; test them with fakes.
- Update the root README with the Eui 2 quick start, architecture, Chatterbox setup, current limitations, and migration status.
- Add an integration test that reaches the pre-encoding plan using fake audio/alignment and does not need GPU, network, or FFmpeg.

Do not add publishing or YouTube integration.
