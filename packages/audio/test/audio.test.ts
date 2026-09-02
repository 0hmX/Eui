import { afterEach, describe, expect, test } from "bun:test";
import { chmod, mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { parseNarration } from "@eui/compiler";
import {
  FakeAudioAligner,
  FakeAudioProvider,
  ChatterboxProvider,
  buildAudio,
  lookupAudio,
  lookupAlignment,
  mapCuesToTimestamps,
  normalizeNarration,
  stableCacheKey,
  writeAlignmentAtomically,
  writeAudioAtomically,
} from "../src";

const temporaryDirectories: string[] = [];

async function temporaryDirectory(): Promise<string> {
  const path = await mkdtemp(join(process.cwd(), ".bun-tmp", "audio-test-"));
  temporaryDirectories.push(path);
  return path;
}

afterEach(async () => {
  await Promise.all(temporaryDirectories.splice(0).map((path) => rm(path, { recursive: true, force: true })));
});

function plan(text = "Hello world", options: Record<string, string | number> = {}) {
  return {
    version: "2",
    settings: { width: 1920, height: 1080, fps: 30 },
    voice: { provider: "fake", voice: "narrator", speed: 1, options },
    scenes: [{
      id: "intro",
      narration: text,
      layers: [{ id: "title", type: "text", props: { color: "red" } }],
      tools: [],
    }],
  };
}

describe("stable audio identity", () => {
  test("normalizes narration and object key order", async () => {
    expect(normalizeNarration("  Cafe\u0301\n\tready  ")).toBe("Café ready");
    expect(await stableCacheKey("test", { b: 2, a: 1 })).toBe(await stableCacheKey("test", { a: 1, b: 2 }));
  });

  test("reuses visual-only edits and invalidates every synthesis input", async () => {
    const root = await temporaryDirectory();
    const reference = join(root, "voice.wav");
    await writeFile(reference, "voice-one");
    const provider = new FakeAudioProvider();
    const aligner = new FakeAudioAligner();
    const common = { cacheDirectory: join(root, "cache"), providers: { fake: provider }, aligner, voiceReferences: { narrator: reference } };

    const first = await buildAudio(plan(), common);
    const visualOnly = plan();
    visualOnly.scenes[0]!.layers[0]!.props.color = "blue";
    const second = await buildAudio(visualOnly, common);
    expect(provider.calls).toHaveLength(1);
    expect(aligner.calls).toHaveLength(1);
    expect(second.scenes[0]).toMatchObject({ audioCacheHit: true, alignmentCacheHit: true });
    expect(second.scenes[0]!.synthesisKey).toBe(first.scenes[0]!.synthesisKey);

    await buildAudio(plan("Hello again"), common);
    await writeFile(reference, "voice-two");
    await buildAudio(plan(), common);
    await buildAudio(plan("Hello world", { exaggeration: 0.8 }), common);
    await buildAudio(plan(), { ...common, seed: 9 });
    expect(provider.calls).toHaveLength(5);
  });

  test("realigns without regenerating when the aligner version changes", async () => {
    const root = await temporaryDirectory();
    const provider = new FakeAudioProvider();
    const cacheDirectory = join(root, "cache");
    await buildAudio(plan(), { cacheDirectory, providers: { fake: provider }, aligner: new FakeAudioAligner("fake", "1") });
    const changed = new FakeAudioAligner("fake", "2");
    const result = await buildAudio(plan(), { cacheDirectory, providers: { fake: provider }, aligner: changed });
    expect(provider.calls).toHaveLength(1);
    expect(changed.calls).toHaveLength(1);
    expect(result.scenes[0]).toMatchObject({ audioCacheHit: true, alignmentCacheHit: false });
  });
});

describe("cue timing", () => {
  test("uses occurrence order for repeats and assigns punctuation to the preceding word", () => {
    const parsed = parseNarration("Go[[cue:comma]], [[cue:again]]go! Now.[[cue:end]]");
    const words = [
      { token: "Go", startMs: 0, endMs: 120 },
      { token: "go", startMs: 200, endMs: 320 },
      { token: "Now", startMs: 400, endMs: 540 },
    ];
    expect(mapCuesToTimestamps(parsed.text, parsed.cues, words, 600)).toEqual({ comma: 120, again: 200, end: 600 });
  });

  test("maps a cue embedded in a word to that occurrence's start", () => {
    const parsed = parseNarration("he[[cue:inside]]llo hello");
    expect(mapCuesToTimestamps(parsed.text, parsed.cues, [
      { token: "hello", startMs: 10, endMs: 100 },
      { token: "hello", startMs: 150, endMs: 250 },
    ], 300)).toEqual({ inside: 10 });
  });
});

test("partial or corrupt cache directories are never accepted as hits", async () => {
  const root = await temporaryDirectory();
  const key = "a".repeat(64);
  const directory = join(root, "audio", key);
  await mkdir(directory, { recursive: true });
  await writeFile(join(directory, "audio.wav"), "incomplete");
  expect(await lookupAudio(root, key)).toBeUndefined();
  await writeFile(join(directory, "manifest.json"), JSON.stringify({
    version: "1",
    kind: "eui.audio",
    synthesisKey: key,
    narrationHash: "b".repeat(64),
    provider: { id: "fake", version: "1" },
    voiceReferenceHash: null,
    artifact: { file: "audio.wav", sha256: "c".repeat(64), bytes: 10, mediaType: "audio/wav" },
  }));
  expect(await lookupAudio(root, key)).toBeUndefined();
});

test("atomic cache writes replace corrupt destinations and preserve valid concurrent winners", async () => {
  const root = await temporaryDirectory();
  const synthesisKey = "d".repeat(64);
  const corruptAudio = join(root, "audio", synthesisKey);
  await mkdir(corruptAudio, { recursive: true });
  await writeFile(join(corruptAudio, "manifest.json"), "not json");
  const base = {
    version: "1" as const,
    kind: "eui.audio" as const,
    synthesisKey,
    narrationHash: "e".repeat(64),
    provider: { id: "fake", version: "1" },
    voiceReferenceHash: null,
  };
  const [first, second] = await Promise.all([
    writeAudioAtomically(root, base, { audio: new TextEncoder().encode("winner-one"), extension: "wav", mediaType: "audio/wav" }),
    writeAudioAtomically(root, base, { audio: new TextEncoder().encode("winner-two"), extension: "wav", mediaType: "audio/wav" }),
  ]);
  expect(first.artifact.sha256).toBe(second.artifact.sha256);
  expect((await lookupAudio(root, synthesisKey))?.artifact.sha256).toBe(first.artifact.sha256);

  const alignmentKey = "f".repeat(64);
  const corruptAlignment = join(root, "alignments", alignmentKey);
  await mkdir(corruptAlignment, { recursive: true });
  await writeFile(join(corruptAlignment, "manifest.json"), "{}");
  const alignment = await writeAlignmentAtomically(root, {
    version: "1",
    kind: "eui.alignment",
    alignmentKey,
    synthesisKey,
    audioSha256: first.artifact.sha256,
    aligner: { id: "fake", version: "1" },
    durationMs: 100,
    words: [{ token: "word", startMs: 0, endMs: 100 }],
  });
  expect(await lookupAlignment(root, alignmentKey)).toEqual(alignment);
});

test("the Chatterbox worker is versioned and imports the submodule only inside the worker", async () => {
  const source = new TextDecoder().decode(await readFile(join(process.cwd(), "workers", "chatterbox", "worker.py")));
  expect(source).toContain('PROTOCOL = "eui.chatterbox"');
  expect(source).toContain("VERSION = 1");
  expect(source).toContain("from chatterbox.tts import ChatterboxTTS");
});

test("the Chatterbox adapter validates the complete JSON-lines response", async () => {
  const root = await temporaryDirectory();
  const fakePython = join(root, "fake-python");
  await writeFile(fakePython, `#!/usr/bin/env bun
const request = JSON.parse(await Bun.stdin.text());
await Bun.write(request.params.outputPath, "wav");
console.log(JSON.stringify({protocol: "eui.chatterbox", version: 1, id: request.id, ok: true, result: {sampleRate: 24000}}));
`);
  await chmod(fakePython, 0o755);
  const provider = new ChatterboxProvider({ python: fakePython, repositoryRoot: root });
  const result = await provider.synthesize({
    text: "hello",
    voice: { provider: "chatterbox", voice: "narrator", speed: 1 },
    seed: 0,
  });
  expect(new TextDecoder().decode(result.audio)).toBe("wav");

  await writeFile(fakePython, `#!/usr/bin/env bun
console.log("not-json");
`);
  await expect(provider.synthesize({
    text: "hello",
    voice: { provider: "chatterbox", voice: "narrator", speed: 1 },
    seed: 0,
  })).rejects.toThrow("invalid JSON");
});
