# Stage 3: Manim renderer and minimal visual tools

Implement the first renderer and initial reusable visual tools.

Implement:

- A renderer contract owned outside core and `packages/renderer-manim` as its implementation.
- A registry that resolves validated tool names to implementations and rejects missing tools before rendering.
- A deliberately small tool set: text, verified local media/image assets, captions, and static code when requested.
- Cue-driven tool start/end timing. Do not implement code-diff animation.
- Deterministic preparation tests and lightweight renderer tests that do not require encoding a complete MP4.

Keep expensive tokenization and asset loading in a preparation phase. Rendering must consume prepared data and must not perform network I/O. Keep Manim behind the renderer adapter boundary.
