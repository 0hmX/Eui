# @eui/audio

Content-addressed narration synthesis and alignment for Eui 2. Synthesis identity
contains normalized narration, provider/version, complete voice configuration,
voice-reference file contents, and seed. Alignment is cached separately, so changing
an aligner can never force an unchanged clip to be synthesized again.

Cache directories become visible only after their audio and commit-last manifest are
complete. Reads verify artifact size and SHA-256 before accepting a hit.

`ChatterboxProvider` communicates with `workers/chatterbox/worker.py` over the
versioned `eui.chatterbox` JSON-lines protocol. The worker imports the existing
`submodule/chatterbox` source through `PYTHONPATH`; tests use the exported deterministic
fake provider and aligner and do not start the worker or load model weights.
