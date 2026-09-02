import { describe, expect, test } from "bun:test";
import { cue, defineVideo, scene } from "@eui/core";
import {
  CompileError,
  compileTimeline,
  millisecondsToFrame,
  millisecondsToFrameInterval,
  parseNarration,
  validateVideoPlan,
} from "../src";

const plan = defineVideo({
  version: "2",
  settings: { width: 1080, height: 1920, fps: 30, background: "#111111" },
  voice: { provider: "chatterbox", voice: "narrator", speed: 1 },
  scenes: [
    scene({
      id: "intro",
      narration: `One ${cue("reveal")}two three`,
      layers: [
        {
          id: "title",
          type: "text",
          props: { text: "Hello", position: [0, 100] },
          from: { type: "cue", cue: "reveal", offsetMs: 0 },
        },
      ],
      tools: [
        {
          id: "accent",
          tool: "text.reveal",
          at: { type: "cue", cue: "reveal", offsetMs: 0 },
          until: { type: "scene-end", offsetMs: -100 },
          input: { color: "yellow" },
        },
      ],
    }),
  ],
});

const alignment = [
  {
    sceneId: "intro",
    durationMs: 1_100,
    words: [
      { token: "One", startMs: 0, endMs: 250 },
      { token: "two", startMs: 400, endMs: 650 },
      { token: "three", startMs: 750, endMs: 1_000 },
    ],
  },
];

describe("canonical video plans", () => {
  test("validates and compiles a valid authored project", () => {
    expect(validateVideoPlan(plan).scenes[0]?.id).toBe("intro");
    const timeline = compileTimeline(plan, alignment);
    expect(timeline).toMatchObject({ fps: 30, durationFrames: 33 });
    expect(timeline.scenes[0]).toMatchObject({
      id: "intro",
      startFrame: 0,
      endFrame: 33,
      cues: { reveal: 12 },
      layers: [{ id: "title", startFrame: 12, endFrame: 33 }],
      tools: [{ id: "accent", frame: 12, startFrame: 12, endFrame: 30 }],
    });
    expect(timeline.scenes[0]?.narration.words).toEqual([
      { token: "One", startFrame: 0, endFrame: 8 },
      { token: "two", startFrame: 12, endFrame: 20 },
      { token: "three", startFrame: 23, endFrame: 30 },
    ]);
  });

  test("reports path-aware schema errors for malformed input", () => {
    expect(() => validateVideoPlan({ ...plan, settings: { ...plan.settings, fps: 0 } })).toThrow("$.settings.fps");
  });
});

describe("narration cue parsing", () => {
  test("extracts clean text and character/token offsets", () => {
    expect(parseNarration(`  Hello   ${cue("diagram")}world. ${cue("end")}`)).toEqual({
      text: "Hello world.",
      tokens: ["Hello", "world."],
      cues: [
        { name: "diagram", characterOffset: 6, tokenOffset: 1 },
        { name: "end", characterOffset: 13, tokenOffset: 2 },
      ],
    });
  });

  test("normalizes Unicode without shifting cue character offsets", () => {
    expect(parseNarration("Cafe\u0301 [[cue:ready]]ready")).toEqual({
      text: "Café ready",
      tokens: ["Café", "ready"],
      cues: [{name: "ready", characterOffset: 5, tokenOffset: 1}],
    });
  });

  test("rejects duplicate cues", () => {
    expect(() => parseNarration("a [[cue:x]] b [[cue:x]] c", ["scenes", 0, "narration"])).toThrow(
      "$.scenes[0].narration: duplicate cue 'x'",
    );
  });

  test("rejects references to missing cues", () => {
    const invalid = {
      ...plan,
      scenes: [{ ...plan.scenes[0]!, layers: [{ id: "x", type: "text", from: { type: "cue", cue: "absent" } }] }],
    };
    expect(() => compileTimeline(invalid, alignment)).toThrow("$.scenes[0].layers[0].from.cue: missing cue 'absent'");
  });

  test("resolves cue boundaries consistently around whitespace and punctuation", () => {
    const boundaryPlan = {
      ...plan,
      scenes: [{
        id: "intro",
        narration: "One [[cue:next]]two. [[cue:sentence]]Three",
        layers: [],
        tools: [],
      }],
    };
    const timeline = compileTimeline(boundaryPlan, [{
      sceneId: "intro",
      durationMs: 1_000,
      words: [
        { token: "One", startMs: 0, endMs: 100 },
        { token: "two", startMs: 200, endMs: 350 },
        { token: "Three", startMs: 500, endMs: 700 },
      ],
    }]);
    expect(timeline.scenes[0]?.cues).toEqual({ next: 6, sentence: 11 });
  });

  test("rejects tool intervals whose cue-driven end precedes the start", () => {
    const invalid = {
      ...plan,
      scenes: [{
        ...plan.scenes[0]!,
        tools: [{
          id: "bad",
          tool: "text",
          at: { type: "scene-end" as const, offsetMs: 0 },
          until: { type: "scene-start" as const, offsetMs: 0 },
        }],
      }],
    };
    expect(() => compileTimeline(invalid, alignment)).toThrow("$.scenes[0].tools[0]: tool end precedes its start");
  });
});

describe("frame rounding", () => {
  test("uses deterministic nearest-frame rounding", () => {
    expect(millisecondsToFrame(16, 30)).toBe(0);
    expect(millisecondsToFrame(17, 30)).toBe(1);
    expect(millisecondsToFrame(500, 30)).toBe(15);
    expect(millisecondsToFrameInterval(17, 50, 30)).toEqual({ startFrame: 1, endFrame: 2 });
  });

  test("rejects invalid intervals", () => {
    expect(() => millisecondsToFrameInterval(20, 10, 30)).toThrow(RangeError);
  });
});

test("alignment errors retain their input paths", () => {
  try {
    compileTimeline(plan, [{ ...alignment[0], words: [{ token: "One", startMs: 0, endMs: 2_000 }] }]);
    throw new Error("expected compilation to fail");
  } catch (error) {
    expect(error).toBeInstanceOf(CompileError);
    expect((error as CompileError).issues).toContainEqual({
      path: ["alignments", 0, "words"],
      message: "expected 3 word timings for narration, received 1",
    });
    expect((error as CompileError).message).toContain("$.alignments[0].words[0].endMs");
  }
});

test("authored ids are unique within their scene collections", () => {
  expect(() => validateVideoPlan({
    ...plan,
    scenes: [{
      ...plan.scenes[0]!,
      layers: [
        { id: "same", type: "text" },
        { id: "same", type: "image" },
      ],
    }],
  })).toThrow("duplicate layer id 'same'");
});
