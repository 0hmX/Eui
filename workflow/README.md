# Eui 2 Codex workflow

This workflow uses the Codex CLI in non-interactive mode to implement Eui 2 in five bounded, sequential stages. Each stage sees the repository state produced by the preceding stage, writes a structured result, and is marked complete only after Codex reports successful verification.

## Run

```sh
./workflow/eui-v2.zsh --dry-run
./workflow/eui-v2.zsh
```

Useful controls:

```sh
./workflow/eui-v2.zsh --from 03-renderer-tools
./workflow/eui-v2.zsh --only 05-review --force
./workflow/eui-v2.zsh --model gpt-5.6-sol
```

The workflow deliberately uses `--ask-for-approval never` and `--sandbox workspace-write`. This keeps execution non-interactive while limiting Codex writes to the repository. A stage stops on command failure or when its structured final result is `blocked`.

State, logs, and structured stage results are stored under `.eui-workflow/`, which is ignored by Git. Delete an individual `.done` marker or use `--force` to rerun work.

The Chatterbox submodule is initialized automatically. YouTube upload and other publishing integrations are outside this workflow.
