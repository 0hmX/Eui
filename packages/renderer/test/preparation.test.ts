import {describe, expect, test} from "bun:test";
import type {CompiledTimeline} from "@eui/compiler";
import {
  ToolRegistryError,
  createShikiTokenizer,
  createDefaultToolRegistry,
  type AssetLoader,
  type CodeTokenizer,
  type PreparedCodeLine,
} from "../src";

const tokenizer: CodeTokenizer = {
  async tokenize(code): Promise<readonly PreparedCodeLine[]> {
    return code.split("\n").map((line) => [{content: line, color: line.includes("const") ? "#c586c0" : "#ffffff"}]);
  },
};

const assetLoader: AssetLoader = {
  async load(source) {
    return {source: `/prepared/${source}`, mimeType: "image/png", width: 640, height: 480};
  },
};

function timeline(tool: string, input: Record<string, any>): CompiledTimeline {
  return {
    fps: 30,
    durationFrames: 90,
    scenes: [{
      id: "scene",
      startFrame: 0,
      endFrame: 90,
      durationMs: 3_000,
      cues: {show: 15, hide: 75},
      layers: [],
      narration: {
        text: "one two",
        tokens: ["one", "two"],
        cues: [],
        words: [
          {token: "one", startFrame: 0, endFrame: 12},
          {token: "two", startFrame: 15, endFrame: 27},
        ],
      },
      tools: [{id: "visual", tool, input, frame: 15, startFrame: 15, endFrame: 75}],
    }],
  };
}

describe("tool preparation", () => {
  test("tokenizes code with Shiki during preparation setup", async () => {
    const shiki = await createShikiTokenizer({languages: ["typescript"]});
    const lines = await shiki.tokenize("const value = 1;", "typescript", "github-dark");
    expect(lines[0]?.map((token) => token.content).join("")).toBe("const value = 1;");
    expect(lines[0]?.every((token) => token.color.startsWith("#"))).toBe(true);
  });

  test("rejects every missing tool before starting expensive preparation", async () => {
    let calls = 0;
    const countingTokenizer: CodeTokenizer = {async tokenize() { calls++; return []; }};
    const input = timeline("missing.tool", {});
    input.scenes[0]!.tools.push({
      id: "code",
      tool: "code",
      input: {source: "const x = 1"},
      frame: 15,
      startFrame: 15,
      endFrame: 75,
    });
    await expect(createDefaultToolRegistry().prepare(input, {tokenizer: countingTokenizer, assetLoader})).rejects.toThrow(
      "missing visual tools: 'missing.tool'",
    );
    expect(calls).toBe(0);
  });

  test("validates tool-specific input with defaults", async () => {
    await expect(createDefaultToolRegistry().prepare(timeline("text", {text: 4}), {tokenizer, assetLoader})).rejects.toBeInstanceOf(
      ToolRegistryError,
    );
    const prepared = await createDefaultToolRegistry().prepare(timeline("text", {text: "Hello"}), {tokenizer, assetLoader});
    expect(prepared.tools[0]).toMatchObject({startFrame: 15, endFrame: 75, visual: {kind: "text"}});
    expect((prepared.tools[0]!.visual.data as any).fontSize).toBe(64);
  });

  test("loads image assets during preparation", async () => {
    const prepared = await createDefaultToolRegistry().prepare(
      timeline("media.image", {source: "hero.png"}),
      {tokenizer, assetLoader},
    );
    expect((prepared.tools[0]!.visual.data as any).asset).toEqual({
      source: "/prepared/hero.png",
      mimeType: "image/png",
      width: 640,
      height: 480,
    });
  });

  test("prepares caption groups from compiled word timing", async () => {
    const prepared = await createDefaultToolRegistry().prepare(
      timeline("captions", {mode: "word"}),
      {tokenizer, assetLoader},
    );
    expect((prepared.tools[0]!.visual.data as any).groups).toEqual([
      {text: "two", startFrame: 15, endFrame: 27, words: [{token: "two", startFrame: 15, endFrame: 27}]},
    ]);
  });

  test("treats caption invocation bounds as half-open", async () => {
    const input = timeline("captions", {mode: "word"});
    input.scenes[0]!.narration.words = [
      {token: "before", startFrame: 0, endFrame: 15},
      {token: "inside", startFrame: 15, endFrame: 27},
      {token: "after", startFrame: 75, endFrame: 80},
    ];
    const prepared = await createDefaultToolRegistry().prepare(input, {tokenizer, assetLoader});
    expect((prepared.tools[0]!.visual.data as any).groups.map((group: any) => group.text)).toEqual(["inside"]);
  });
});
