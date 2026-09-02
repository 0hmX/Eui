import { afterEach, describe, expect, test } from "bun:test";
import { FakeAudioAligner, FakeAudioProvider } from "@eui/audio";
import type { PreparedRenderPlan } from "@eui/renderer";
import { chmod, mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { CommandAligner, inspectProject, prepareProject, renderProject, runCli, type EncodingAdapter } from "../src";

const temporary: string[] = [];
afterEach(async () => { await Promise.all(temporary.splice(0).map((path) => rm(path, { recursive: true, force: true }))); });

class FakeEncoder implements EncodingAdapter {
  readonly id = "fake-encoder";
  readonly version = "1";
  renderCalls = 0;
  async render(plan: PreparedRenderPlan, output: string) { this.renderCalls++; await Bun.write(output, `FAKE-MP4 ${plan.durationFrames}`); }
  async concatenateAudio(inputs: readonly string[], output: string) { await Bun.write(output, await Bun.file(inputs[0]!).arrayBuffer()); }
  async mux(video: string, narration: string, output: string) { await Bun.write(output, `MUX ${await Bun.file(video).text()} ${await Bun.file(narration).text()}`); }
}

async function fixture(): Promise<string> {
  const root = await mkdtemp(join(process.cwd(), ".bun-tmp", "cli-test-"));
  temporary.push(root);
  await writeFile(join(root, "eui.json"), JSON.stringify({
    version: "2", settings: { width: 1080, height: 1920, fps: 30 },
    voice: { provider: "fake", voice: "narrator" },
    scenes: [{
      id: "demo", narration: "Make it typed. [[cue:change]]Now catch mistakes.", layers: [],
      tools: [
        { id: "captions", tool: "captions", at: { type: "scene-start" }, input: { mode: "phrase" } },
        { id: "title", tool: "text", at: { type: "cue", cue: "change" }, input: { text: "Typed output" } },
      ],
    }],
  }));
  return root;
}

function services(encoder = new FakeEncoder()) {
  return { providers: { fake: new FakeAudioProvider() }, aligner: new FakeAudioAligner(), encoder };
}

describe("Eui 2 build graph", () => {
  test("reaches a deterministic pre-encoding plan without network, GPU, or FFmpeg", async () => {
    const project = await fixture();
    const encoder = new FakeEncoder();
    const result = await prepareProject(project, services(encoder));
    expect(result.timeline.durationFrames).toBeGreaterThan(0);
    expect(result.prepared.tools.map((tool) => tool.visual.kind)).toEqual(["captions", "text"]);
    expect(encoder.renderCalls).toBe(0);
    const inspection = await inspectProject(project);
    expect(inspection.scenes[0]?.resolvedCueMs?.change).toBe(540);
    expect(inspection.stages.find((stage) => stage.stage === "prepare")?.state).toBe("fresh");

    const source = join(project, "eui.json");
    const changed = JSON.parse(await readFile(source, "utf8"));
    changed.settings.background = "#ffffff";
    await writeFile(source, JSON.stringify(changed));
    const stale = await inspectProject(project);
    expect(stale.stages.find((stage) => stage.stage === "validate")).toMatchObject({ state: "stale", reason: "validated project content changed" });
    expect(stale.stages.find((stage) => stage.stage === "audio")?.state).toBe("fresh");
    expect(stale.stages.find((stage) => stage.stage === "prepare")).toMatchObject({ state: "stale", reason: "dependency 'validate' is stale or has a different cache key" });
    expect(encoder.renderCalls).toBe(0);
  });

  test("fakes render, mux, captions, manifest, and resumes unchanged work", async () => {
    const project = await fixture();
    const encoder = new FakeEncoder();
    const configured = services(encoder);
    const paths = await renderProject(project, configured);
    await renderProject(project, configured);
    expect(encoder.renderCalls).toBe(1);
    expect(await readFile(paths.srt, "utf8")).toContain("Make it typed.");
    expect(await readFile(paths.vtt, "utf8")).toStartWith("WEBVTT");
    const manifest = JSON.parse(await readFile(paths.manifest, "utf8"));
    expect(manifest.outputs.map((item: { path: string }) => item.path)).toEqual(["dist/video.mp4", "dist/narration.wav", "dist/captions.srt", "dist/captions.vtt"]);
  });

  test("CLI returns usage and validation exit codes with JSON errors", async () => {
    const output: string[] = [];
    const errors: string[] = [];
    expect(await runCli(["unknown", "project", "--json"], { log: (line) => output.push(line), error: (line) => errors.push(line) })).toBe(2);
    expect(JSON.parse(errors[0]!)).toMatchObject({ ok: false, error: "unknown command 'unknown'" });
    expect(await runCli(["doctor", "extra", "--json"], { log: (line) => output.push(line), error: (line) => errors.push(line) })).toBe(2);
    expect(JSON.parse(errors.at(-1)!)).toMatchObject({ ok: false, error: "unexpected argument 'extra'" });
    expect(await runCli(["--json"], { log: (line) => output.push(line), error: (line) => errors.push(line) })).toBe(2);
    expect(JSON.parse(errors.at(-1)!)).toMatchObject({ ok: false, error: "missing command" });
    expect(await runCli(["help", "--json"], { log: (line) => output.push(line), error: (line) => errors.push(line) })).toBe(0);
    expect(JSON.parse(output.at(-1)!)).toMatchObject({ ok: true });
  });

  test("command alignment uses a correlated and validated protocol envelope", async () => {
    const root = await fixture();
    const command = join(root, "fake-aligner");
    await writeFile(command, `#!/usr/bin/env bun
const request = JSON.parse(await Bun.stdin.text());
console.log(JSON.stringify({protocol: "eui.aligner", version: 1, id: request.id, ok: true, result: {
  durationMs: 100, words: [{token: "hello", startMs: 0, endMs: 100}]
}}));
`);
    await chmod(command, 0o755);
    const aligner = new CommandAligner(command);
    const result = await aligner.align({
      audio: new TextEncoder().encode("audio"), audioSha256: "a".repeat(64),
      text: "hello", tokens: ["hello"], mediaType: "audio/wav",
    });
    expect(result).toEqual({durationMs: 100, words: [{token: "hello", startMs: 0, endMs: 100}]});

    await writeFile(command, `#!/usr/bin/env bun
console.log(JSON.stringify({protocol: "eui.aligner", version: 1, id: "wrong", ok: true, result: {durationMs: 0, words: []}}));
`);
    await expect(aligner.align({
      audio: new Uint8Array([1]), audioSha256: "b".repeat(64), text: "hello", tokens: ["hello"], mediaType: "audio/wav",
    })).rejects.toThrow("invalid protocol response");
  });
});
