# Stage 2: Content-addressed audio pipeline

Implement the audio subsystem on top of the existing foundation.

Implement:

- `packages/audio` with provider and aligner interfaces, normalized narration hashing, a stable cache-key algorithm, manifests, cache lookup/write behavior, and orchestration that never regenerates unchanged clips.
- A Chatterbox provider that invokes a versioned JSON-lines Python worker under `workers/chatterbox`. Keep model loading inside the worker. Communicate through stdin/stdout or explicit request/response files; never interpolate narration into shell source.
- A deterministic fake provider and fake aligner for unit and integration tests.
- Mapping from cue character/token offsets to aligned timestamps with clear behavior around punctuation and repeated words.
- Atomic artifact writes so interrupted generation does not create valid-looking cache entries.
- Tests proving visual-only changes reuse audio, while narration, voice reference, model options, or seed changes invalidate it.

Do not download model weights or execute Chatterbox in tests. Use the existing Chatterbox git submodule rather than copying its source.
