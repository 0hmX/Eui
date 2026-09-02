# Stage 1: TypeScript foundation and canonical video plan

Create the minimal Bun workspace foundation for Eui 2 without removing the legacy Python CLI.

Implement:

- Root Bun workspace scripts for typechecking and testing.
- `packages/schema`: Zod schemas and inferred public TypeScript types for project settings, voice configuration, scenes, narration, cue markers, layers, timing anchors, tool invocations, and build manifests.
- `packages/core`: `defineVideo`, `scene`, and `cue` authoring helpers that preserve strong inference while emitting JSON-compatible data.
- `packages/compiler`: validation and a renderer-independent timeline compiler. Parse `[[cue:name]]` markers, produce clean TTS text, retain cue character/token offsets, reject duplicate or missing cue references, convert aligned millisecond timestamps to deterministic frame intervals, and report useful path-aware errors.
- Tests covering valid projects, malformed input, cue extraction, missing cues, duplicate cues, and frame rounding.
- Public exports and short package READMEs where they clarify boundaries.

Avoid renderer dependencies in schema/core/compiler. Avoid placeholder APIs that cannot be exercised in tests.
