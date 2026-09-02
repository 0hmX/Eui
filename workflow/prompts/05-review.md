# Stage 5: Integration review and repair

Review the complete Eui 2 implementation as a maintainer, then fix problems you find rather than only reporting them.

Check package boundaries and exports; validation of authored data; cue-to-frame off-by-one behavior; audio cache atomicity and invalidation; safe child processes and JSON protocol handling; code diff identity across inserts, deletes, modifications, and moves; CLI exit codes and errors; and deterministic offline tests.

Run the full Bun verification suite and repair failures. Tests must not need network, GPUs, model weights, browsers, or FFmpeg. Do not introduce YouTube publishing. Keep the legacy Python implementation intact except for compatibility with removal of its unused YouTube dependency.
