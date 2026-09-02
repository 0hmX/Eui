#!/usr/bin/env zsh

set -euo pipefail

script_dir=${0:A:h}
repo_root=${script_dir:h}
schema_file="$script_dir/stage-result.schema.json"
context_file="$script_dir/prompts/context.md"
state_dir="$repo_root/.eui-workflow"

typeset -a stages
stages=(
  "01-foundation"
  "02-audio"
  "03-renderer-tools"
  "04-cli-example"
  "05-review"
)

dry_run=0
force=0
from_stage=""
only_stage=""
codex_model=""

usage() {
  print -r -- "Usage: workflow/eui-v2.zsh [--dry-run] [--force] [--from STAGE] [--only STAGE] [--model MODEL]"
  print -r -- ""
  print -r -- "Runs the Eui 2 implementation stages through 'codex exec' in non-interactive mode."
  print -r -- "Completed stages are recorded in .eui-workflow and skipped on subsequent runs."
  print -r -- ""
  print -r -- "Stages: ${stages[*]}"
}

stage_exists() {
  local candidate=$1
  local stage
  for stage in "${stages[@]}"; do
    [[ "$stage" == "$candidate" ]] && return 0
  done
  return 1
}

while (( $# > 0 )); do
  case "$1" in
    --dry-run)
      dry_run=1
      shift
      ;;
    --force)
      force=1
      shift
      ;;
    --from)
      (( $# >= 2 )) || { print -u2 -- "--from requires a stage"; exit 2; }
      from_stage=$2
      shift 2
      ;;
    --only)
      (( $# >= 2 )) || { print -u2 -- "--only requires a stage"; exit 2; }
      only_stage=$2
      shift 2
      ;;
    --model)
      (( $# >= 2 )) || { print -u2 -- "--model requires a model name"; exit 2; }
      codex_model=$2
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      print -u2 -- "Unknown argument: $1"
      usage >&2
      exit 2
      ;;
  esac
done

[[ -z "$from_stage" ]] || stage_exists "$from_stage" || {
  print -u2 -- "Unknown --from stage: $from_stage"
  exit 2
}
[[ -z "$only_stage" ]] || stage_exists "$only_stage" || {
  print -u2 -- "Unknown --only stage: $only_stage"
  exit 2
}
[[ -z "$from_stage" || -z "$only_stage" ]] || {
  print -u2 -- "Use either --from or --only, not both"
  exit 2
}

command -v codex >/dev/null || { print -u2 -- "codex CLI is required"; exit 127; }
command -v bun >/dev/null || { print -u2 -- "Bun is required"; exit 127; }
git -C "$repo_root" rev-parse --is-inside-work-tree >/dev/null 2>&1 || {
  print -u2 -- "Eui workflow must run from a Git checkout"
  exit 2
}

if (( ! dry_run )); then
  mkdir -p "$state_dir/logs" "$state_dir/results"
  git -C "$repo_root" submodule update --init --recursive -- submodule/chatterbox
fi

started=0
for stage in "${stages[@]}"; do
  if [[ -n "$only_stage" && "$stage" != "$only_stage" ]]; then
    continue
  fi
  if [[ -n "$from_stage" && "$stage" == "$from_stage" ]]; then
    started=1
  fi
  if [[ -n "$from_stage" && $started -eq 0 ]]; then
    continue
  fi

  prompt_file="$script_dir/prompts/$stage.md"
  done_file="$state_dir/$stage.done"
  result_file="$state_dir/results/$stage.json"
  log_file="$state_dir/logs/$stage.log"

  [[ -f "$prompt_file" ]] || { print -u2 -- "Missing prompt: $prompt_file"; exit 2; }

  if (( ! force )) && [[ -f "$done_file" ]]; then
    print -r -- "Skipping completed stage: $stage"
    continue
  fi

  if (( ! force && ! dry_run )) && [[ -f "$result_file" ]] && bun -e '
    const value = await Bun.file(process.argv[1]).json();
    process.exit(value.status === "complete" ? 0 : 1);
  ' "$result_file"; then
    print -r -- "completed_at=$(date +%s)" > "$done_file"
    print -r -- "Recovered completed stage: $stage"
    continue
  fi

  print -r -- "Running stage: $stage"
  if (( dry_run )); then
    print -r -- "  prompt: $prompt_file"
    print -r -- "  result: $result_file"
    continue
  fi

  typeset -a codex_args
  codex_args=(
    --ask-for-approval never
    exec
    --ephemeral
    --color never
    --sandbox workspace-write
    --cd "$repo_root"
    --output-schema "$schema_file"
    --output-last-message "$result_file"
  )
  if [[ -n "$codex_model" ]]; then
    codex_args+=(--model "$codex_model")
  fi
  codex_args+=(-)

  if ! { print -r -- "$(<"$context_file")"; print; print -r -- "$(<"$prompt_file")"; } |
      codex "${codex_args[@]}" >"$log_file" 2>&1; then
    print -u2 -- "Stage failed: $stage"
    print -u2 -- "See $log_file"
    exit 1
  fi

  if ! bun -e '
    const path = process.argv[1];
    const value = await Bun.file(path).json();
    if (value.status !== "complete") {
      console.error(value.summary || `Stage reported ${value.status}`);
      for (const item of value.remaining ?? []) console.error(`- ${item}`);
      process.exit(1);
    }
  ' "$result_file"; then
    print -u2 -- "Stage did not complete: $stage"
    print -u2 -- "See $result_file and $log_file"
    exit 1
  fi

  print -r -- "completed_at=$(date +%s)" > "$done_file"
  print -r -- "Completed stage: $stage"
done

print -r -- "Eui 2 workflow finished."
