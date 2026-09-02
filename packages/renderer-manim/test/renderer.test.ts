import {describe, expect, test} from "bun:test";
import type {PreparedRenderPlan} from "@eui/renderer";
import {ManimRenderer} from "../src";

describe("ManimRenderer", () => {
  test("seals a deterministic local render plan", () => {
    const prepared: PreparedRenderPlan = {
      fps: 30,
      durationFrames: 60,
      tools: [{
        id: "title",
        tool: "text",
        sceneId: "intro",
        startFrame: 0,
        endFrame: 60,
        visual: {kind: "text", data: {text: "board"}},
      }],
    };
    expect(new ManimRenderer().render(prepared)).toEqual({
      engine: "manim",
      fps: 30,
      durationFrames: 60,
      prepared,
    });
  });
});
