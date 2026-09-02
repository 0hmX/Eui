import {cue, defineVideo, scene} from "../../packages/core/src/index";

export default defineVideo({
  version: "2",
  settings: {width: 720, height: 1280, fps: 30, background: "#0d0d0d"},
  voice: {provider: "system", voice: "Samantha", speed: 1},
  scenes: [scene({
    id: "board-element",
    narration: `In tscircuit, the board element is the root of your printed circuit board.${cue("root")} Think of it like the body element in HTML: components and traces live inside it.${cue("size")} Width and height define the physical board size in millimeters.${cue("layers")} Set layers to four when you need two internal copper layers.${cue("routing")} During placement, routingDisabled gives faster previews. Remove it before your final routing checks.${cue("finish")} You can also control the outline, material, thickness, solder mask, and manufacturing clearances.`,
    tools: [
      {
        id: "captions",
        tool: "captions",
        at: {type: "scene-start", offsetMs: 0},
        until: {type: "scene-end", offsetMs: 0},
        input: {mode: "phrase", maxWords: 7, position: [0, 475], fontSize: 34, activeColor: "#ffb000"},
      },
      {
        id: "intro-title",
        tool: "text",
        at: {type: "scene-start", offsetMs: 0},
        until: {type: "cue", cue: "root", offsetMs: 0},
        input: {text: "The <board /> element", position: [0, -475], fontSize: 58, color: "#ffffff"},
      },
      {
        id: "root-callout",
        tool: "text",
        at: {type: "cue", cue: "root", offsetMs: 0},
        until: {type: "cue", cue: "size", offsetMs: 0},
        input: {text: "ROOT CONTAINER", position: [0, -475], fontSize: 42, color: "#ffb000"},
      },
      {
        id: "size-callout",
        tool: "text",
        at: {type: "cue", cue: "size", offsetMs: 0},
        until: {type: "cue", cue: "layers", offsetMs: 0},
        input: {text: "40 mm × 30 mm", position: [0, -475], fontSize: 46, color: "#68d391"},
      },
      {
        id: "layer-callout",
        tool: "text",
        at: {type: "cue", cue: "layers", offsetMs: 0},
        until: {type: "cue", cue: "routing", offsetMs: 0},
        input: {text: "4-LAYER STACKUP", position: [0, -475], fontSize: 42, color: "#58a6ff"},
      },
      {
        id: "routing-callout",
        tool: "text",
        at: {type: "cue", cue: "routing", offsetMs: 0},
        until: {type: "cue", cue: "finish", offsetMs: 0},
        input: {text: "FAST PLACEMENT MODE", position: [0, -475], fontSize: 40, color: "#f778ba"},
      },
      {
        id: "finish-callout",
        tool: "text",
        at: {type: "cue", cue: "finish", offsetMs: 0},
        until: {type: "scene-end", offsetMs: 0},
        input: {text: "SHAPE • MATERIAL • RULES", position: [0, -475], fontSize: 38, color: "#ffb000"},
      },
    ],
  })],
});
