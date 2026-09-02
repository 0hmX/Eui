# `<board />` explainer

A vertical Manim video about tscircuit's `<board />` element. PCB, schematic, and
3D assets are generated from checked tscircuit source; no PCB illustration is
invented by the renderer.

Render the local demo with:

```sh
./scripts/render-board-example.zsh
```

The script runs tscircuit netlist and placement checks, builds real render assets,
then renders the animation with Manim. FFmpeg only extracts the preview frame.
