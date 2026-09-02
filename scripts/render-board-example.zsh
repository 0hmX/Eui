#!/bin/zsh
set -euo pipefail

repo_dir="${0:A:h:h}"
example_dir="$repo_dir/examples/board-explainer"
circuit_file="$example_dir/board.circuit.tsx"
placement_circuit_file="$example_dir/board-routing-disabled.circuit.tsx"
render_dir="$repo_dir/dist/examples/board-explainer/board"
placement_render_dir="$repo_dir/dist/examples/board-explainer/board-routing-disabled"
media_dir="$example_dir/.manim"
output_dir="$example_dir/dist"

cd "$repo_dir"

bunx tsci check netlist "$circuit_file"
bunx tsci check schematic-placement "$circuit_file"
bunx tsci check placement "$circuit_file"
bunx tsci build "$circuit_file" --pcb-png --schematic-png --3d-png --ignore-warnings
bunx tsci check netlist "$placement_circuit_file"
bunx tsci check placement "$placement_circuit_file"
bunx tsci build "$placement_circuit_file" --pcb-png --ignore-warnings

test -f "$render_dir/pcb.png"
test -f "$render_dir/schematic.png"
test -f "$render_dir/3d.png"
test -f "$placement_render_dir/pcb.png"
test -f "$output_dir/narration.wav"

mkdir -p "$media_dir" "$output_dir"

"$repo_dir/.venv-manim/bin/manim" \
  --media_dir "$media_dir" \
  --format mp4 \
  --quality h \
  "$example_dir/manim_scene.py" BoardExplainer

rendered_video="$media_dir/videos/manim_scene/1280p30/BoardExplainer.mp4"
test -f "$rendered_video"
cp "$rendered_video" "$output_dir/video.mp4"

ffmpeg -y -ss 00:00:11 -i "$output_dir/video.mp4" -frames:v 1 "$output_dir/preview.png" >/dev/null 2>&1
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate -show_entries format=duration \
  -of default=noprint_wrappers=1 "$output_dir/video.mp4"
