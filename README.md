# Eui

Eui 2 turns a declarative narration script into a deterministic vertical video.
It is a TypeScript-first, Bun workspace developed alongside the legacy Python
prototype. Authored projects compile to validated data; renderers never execute
model-generated animation code.

## Eui 2 quick start

Install the workspace and validate the included example:

```sh
bun install
bun run eui validate examples/board-explainer
bun run eui inspect examples/board-explainer
```

An Eui project is a directory containing `eui.ts` or `eui.json`. The board
explainer pairs narration cues with checked, locally rendered tscircuit assets.

The non-interactive CLI commands are:

```text
eui validate <project>   validate authored input
eui voice <project>      synthesize/reuse narration and align words
eui preview <project>    compile and prepare the pre-encoding render plan
eui render <project>     render, mux, caption, and write the manifest
eui inspect <project>    explain cues, durations, cache keys, and stale stages
eui doctor               report local runtime and adapter availability
```

Pass `--json` to any command for machine-readable output. Commands do not prompt;
exit code 0 means success, 1 means a build/runtime failure, and 2 means invalid
CLI usage. `inspect` is read-only and never invokes TTS, alignment, rendering, or
encoding.

A completed build writes:

```text
<project>/dist/video.mp4
<project>/dist/narration.wav
<project>/dist/captions.srt
<project>/dist/captions.vtt
<project>/dist/manifest.json
```

Content-addressed cache data and the resumable stage graph live under
`<project>/.eui/`. Visual-only edits change preparation/render keys but retain the
immutable narration cache.

## Architecture

- `@eui/schema` defines strict Zod schemas for authored and build data.
- `@eui/core` supplies the declarative `defineVideo`, `scene`, and `cue` helpers.
- `@eui/compiler` validates plans, resolves narration cues against word timing,
  and compiles renderer-independent frame timelines.
- `@eui/audio` owns provider interfaces, immutable content-addressed narration,
  alignment caches, and the isolated Chatterbox adapter.
- `@eui/renderer` validates and prepares the compact visual tool set: text,
  verified local images, captions, and static code.
- `@eui/renderer-manim` seals prepared data for the Manim adapter boundary.
- `@eui/cli` joins these packages into the `validate → audio → alignment → prepare
  → render → mux → captions → manifest` graph.

Audio is synthesized before animation timing. Cues and captions use aligned word
timings, and generated narration is keyed only by narration, voice/provider,
reference audio, and seed—not visual content.

## Chatterbox and local adapters

Initialize the Chatterbox submodule and install its Python environment according
to [`submodule/chatterbox/README.md`](submodule/chatterbox/README.md). Eui launches
the small JSON-lines worker at `workers/chatterbox/worker.py`; the TypeScript
process does not import or download the model. Tests always use fakes.

The local workflow currently expects two command adapters on `PATH`:

- `eui-align` reads one `eui.aligner` v1 JSON request from stdin and returns a
  matching response envelope containing `{durationMs, words}` alignment data.
- `eui-manim-render --output <path>` reads a prepared plan from stdin and
  writes a silent MP4.

FFmpeg is used only to concatenate multi-scene WAV files and mux final audio. Set
`EUI_ALIGN_COMMAND`, `EUI_RENDER_COMMAND`, or `EUI_FFMPEG` to select alternative
local binaries. A one-scene narration WAV is copied directly and does not require
FFmpeg. Run `bun run eui doctor --json` to see which optional adapters are present.

## Current limitations

- Rendering and forced alignment are adapter contracts; this repository does not
  yet ship their production command binaries.
- Manim is the animation renderer, and the tool set is intentionally compact.
- Assets must be local. Network assets, cloud services, script-generation APIs,
  GUI editing, publishing, and YouTube upload are out of scope.
- Unit and integration tests stop at deterministic plans or use fake encoders, so
  they need no network, GPU, model download, or FFmpeg.

## Migration status

Eui 2 now includes the schema/core DSL, cue compiler, content-addressed audio and
alignment pipeline, visual preparation tools, Manim adapter, CLI, build
graph, captions, manifest generation, and an offline end-to-end integration test.
The legacy Python sources under `src/` and `bin/eui.py` remain available as
reference during migration; Eui 2 does not remove or route through them.

## Development

Use Bun exclusively for TypeScript dependencies, scripts, and tests:

```sh
bun run typecheck
bun test
```
