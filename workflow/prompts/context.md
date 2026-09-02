# Shared implementation context

You are implementing Eui 2 inside the existing Eui repository. Work directly in the repository and make the requested changes; do not merely describe them and do not create commits.

Eui 2 takes a human-authored narration script and produces a deterministic video. It is TypeScript-first and Bun-based. Its canonical intermediate representation is validated data, never arbitrary model-generated rendering code. Audio is synthesized or reused before animation timing is compiled. Visual actions anchor to narration cues and word timing. Manim is the sole animation renderer, while core packages remain renderer-independent. Chatterbox is the default local TTS provider through an isolated Python worker and must be mocked in tests.

For any tscircuit subject, load and follow the tscircuit skill. Visuals of circuits or boards must be real artifacts produced by `tsci build`, `tsci snapshot`, or another documented tscircuit export. Never fabricate a PCB illustration unless the user explicitly requests illustration. Keep the tool vocabulary deliberately small and do not add code-diff animation.

The legacy Python implementation is reference material and should remain usable during the migration. YouTube upload/publishing is explicitly out of scope. Do not add cloud services, API-based script generation, browser automation, or a GUI editor.

Read `AGENTS.md`, existing manifests, the nearest relevant source, and work completed by earlier stages. Use Bun only for TypeScript dependencies and scripts. Run focused tests and type checks for your stage. Keep the worktree's unrelated changes intact.

Your final response must satisfy the supplied JSON schema. Use `complete` only when this stage is implemented and verified. Use `blocked` when a concrete dependency prevents completion, and list the exact unresolved work.
