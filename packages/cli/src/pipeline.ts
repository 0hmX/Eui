import { buildAudio, sha256, stableJson, type AudioBuildResult } from "@eui/audio";
import { compileTimeline } from "@eui/compiler";
import { createDefaultToolRegistry, createShikiTokenizer, type AssetLoader, type PreparedRenderPlan } from "@eui/renderer";
import { ManimRenderer } from "@eui/renderer-manim";
import { buildManifestSchema, type BuildAsset, type VideoPlan } from "@eui/schema";
import { mkdir, readFile, stat, writeFile } from "node:fs/promises";
import { dirname, relative, resolve } from "node:path";
import { buildCaptionFiles } from "./captions";
import { contentKey, isFresh, readGraph, recordStage, writeGraph } from "./graph";
import { loadProject, resolveProject } from "./project";
import type { BuildGraph, BuildServices, PreEncodingPlan, ProjectPaths } from "./types";

export async function validateProject(project: string): Promise<{ plan: VideoPlan; paths: ProjectPaths; graph: BuildGraph; key: string }> {
  const paths = await resolveProject(project);
  const plan = await loadProject(paths);
  const graph = await readGraph(paths);
  const key = await contentKey("eui.stage.validate.v1", plan);
  if (!(await isFresh(graph.stages.validate, key))) {
    await mkdir(paths.stateDirectory, { recursive: true });
    const artifact = `${paths.stateDirectory}/validated-plan.json`;
    await writeFile(artifact, `${stableJson(plan)}\n`);
    await recordStage(graph, "validate", key, {}, [artifact], { scenes: plan.scenes.length, dimensions: `${plan.settings.width}x${plan.settings.height}` });
    await writeGraph(paths, graph);
  }
  return { plan, paths, graph, key };
}

export async function buildVoice(project: string, services: BuildServices): Promise<{ plan: VideoPlan; paths: ProjectPaths; graph: import("./types").BuildGraph; key: string; audio: AudioBuildResult }> {
  const validated = await validateProject(project);
  const audio = await buildAudio(validated.plan, { cacheDirectory: validated.paths.cacheDirectory, providers: services.providers, aligner: services.aligner });
  await mkdir(validated.paths.stateDirectory, { recursive: true });
  await writeFile(validated.paths.audioBuild, `${stableJson(audio as never)}\n`);
  const audioKey = await contentKey("eui.stage.audio.v1", audio.scenes.map((scene) => ({ sceneId: scene.sceneId, synthesisKey: scene.synthesisKey, sha256: scene.audio.sha256 })));
  const audioInputsKey = await contentKey("eui.stage.audio-inputs.v1", {
    voice: validated.plan.voice,
    scenes: validated.plan.scenes.map((scene) => ({ id: scene.id, narration: scene.narration })),
  });
  const alignmentKey = await contentKey("eui.stage.alignment.v1", audio.scenes.map((scene) => ({ sceneId: scene.sceneId, alignmentKey: scene.alignmentKey })));
  const narrationFresh = validated.graph.stages.audio?.key === audioKey
    && await stat(validated.paths.narration).then((item) => item.isFile()).catch(() => false);
  if (!narrationFresh) {
    await services.encoder.concatenateAudio(audio.scenes.map((scene) => scene.audio.path), validated.paths.narration);
  }
  await recordStage(validated.graph, "audio", audioKey, { validate: validated.key }, [...audio.scenes.map((scene) => scene.audio.path), validated.paths.narration], {
    audioInputsKey,
    cacheKeys: Object.fromEntries(audio.scenes.map((scene) => [scene.sceneId, scene.synthesisKey])),
  });
  await recordStage(validated.graph, "alignment", alignmentKey, { audio: audioKey }, [validated.paths.audioBuild], {
    cacheKeys: Object.fromEntries(audio.scenes.map((scene) => [scene.sceneId, scene.alignmentKey])),
    durationsMs: Object.fromEntries(audio.scenes.map((scene) => [scene.sceneId, scene.durationMs])),
    cuesMs: Object.fromEntries(audio.scenes.map((scene) => [scene.sceneId, scene.cueTimesMs])),
  });
  await writeGraph(validated.paths, validated.graph);
  return { ...validated, audio };
}

export async function prepareProject(project: string, services: BuildServices): Promise<PreEncodingPlan> {
  const voiced = await buildVoice(project, services);
  const alignments = voiced.audio.scenes.map((scene) => ({ sceneId: scene.sceneId, durationMs: scene.durationMs, words: scene.words }));
  const timeline = compileTimeline(voiced.plan, alignments);
  const alignmentKey = voiced.graph.stages.alignment!.key;
  const key = await contentKey("eui.stage.prepare.v1", { validate: voiced.key, alignment: alignmentKey, tools: "default-tools-v1", tokenizer: "shiki-v1" });
  if (await isFresh(voiced.graph.stages.prepare, key)) {
    const cached = JSON.parse(await readFile(voiced.paths.preparedPlan, "utf8")) as { prepared: PreparedRenderPlan };
    return { plan: voiced.plan, audio: voiced.audio, timeline, prepared: cached.prepared, paths: voiced.paths };
  }
  const languages = [...new Set(voiced.plan.scenes.flatMap((scene) => scene.tools.flatMap((tool) => {
    const language = tool.input.language;
    return typeof language === "string" ? [language] : [];
  })))];
  const tokenizer = await createShikiTokenizer({ languages: languages.length ? languages : ["typescript"] });
  const assetLoader: AssetLoader = { async load(source) {
    if (/^(?:https?:)?\/\//i.test(source)) throw new Error(`network assets are not allowed: ${source}`);
    const path = resolve(voiced.paths.root, source);
    const info = await stat(path);
    if (!info.isFile()) throw new Error(`asset is not a file: ${path}`);
    return { source: path };
  } };
  const prepared = await createDefaultToolRegistry().prepare(timeline, { tokenizer, assetLoader });
  await writeFile(voiced.paths.preparedPlan, `${stableJson({ timeline, prepared } as never)}\n`);
  await recordStage(voiced.graph, "prepare", key, { validate: voiced.key, alignment: alignmentKey }, [voiced.paths.preparedPlan], {
    durationFrames: timeline.durationFrames,
    cues: Object.fromEntries(timeline.scenes.map((scene) => [scene.id, scene.cues])),
  });
  await writeGraph(voiced.paths, voiced.graph);
  return { plan: voiced.plan, audio: voiced.audio, timeline, prepared, paths: voiced.paths };
}

export async function renderProject(project: string, services: BuildServices): Promise<ProjectPaths> {
  const pre = await prepareProject(project, services);
  const graph = await readGraph(pre.paths);
  const prepareKey = graph.stages.prepare!.key;
  const manim = new ManimRenderer().render(pre.prepared);
  const framePlan = { renderer: "manim", fps: manim.fps, durationFrames: manim.durationFrames, prepared: pre.prepared };
  await writeFile(pre.paths.framePlan, `${stableJson(framePlan as never)}\n`);
  const renderKey = await contentKey("eui.stage.render.v1", { prepareKey, adapter: { id: services.encoder.id, version: services.encoder.version } });
  if (!(await isFresh(graph.stages.render, renderKey))) {
    await services.encoder.render(pre.prepared, pre.paths.videoOnly);
    await recordStage(graph, "render", renderKey, { prepare: prepareKey }, [pre.paths.framePlan, pre.paths.videoOnly]);
  }
  const narrationHash = await hashPath(pre.paths.narration);
  const muxKey = await contentKey("eui.stage.mux.v1", { renderKey, narrationHash, adapter: { id: services.encoder.id, version: services.encoder.version } });
  if (!(await isFresh(graph.stages.mux, muxKey))) {
    await services.encoder.mux(pre.paths.videoOnly, pre.paths.narration, pre.paths.video);
    await recordStage(graph, "mux", muxKey, { render: renderKey, audio: graph.stages.audio!.key }, [pre.paths.narration, pre.paths.video]);
  }
  const captions = buildCaptionFiles(pre.timeline);
  const captionsKey = await contentKey("eui.stage.captions.v1", { alignment: graph.stages.alignment!.key, captions });
  if (!(await isFresh(graph.stages.captions, captionsKey))) {
    await mkdir(pre.paths.outputDirectory, { recursive: true });
    await Promise.all([writeFile(pre.paths.srt, captions.srt), writeFile(pre.paths.vtt, captions.vtt)]);
    await recordStage(graph, "captions", captionsKey, { alignment: graph.stages.alignment!.key }, [pre.paths.srt, pre.paths.vtt]);
  }
  const outputPaths = [pre.paths.video, pre.paths.narration, pre.paths.srt, pre.paths.vtt];
  const assets = await Promise.all(outputPaths.map((path) => asset(pre.paths, path)));
  const planHash = await sha256(stableJson(pre.plan));
  const manifest = buildManifestSchema.parse({
    version: "1", planHash,
    audio: Object.fromEntries(pre.audio.scenes.map((scene) => [scene.sceneId, { path: relative(pre.paths.root, scene.audio.path), sha256: scene.audio.sha256, bytes: scene.audio.bytes }])),
    outputs: assets,
  });
  const manifestKey = await contentKey("eui.stage.manifest.v1", { muxKey, captionsKey, manifest });
  if (!(await isFresh(graph.stages.manifest, manifestKey))) {
    await writeFile(pre.paths.manifest, `${stableJson(manifest)}\n`);
    await recordStage(graph, "manifest", manifestKey, { mux: muxKey, captions: captionsKey }, [pre.paths.manifest], { outputs: outputPaths });
  }
  await writeGraph(pre.paths, graph);
  return pre.paths;
}

async function hashPath(path: string): Promise<string> { return sha256(await readFile(path)); }
async function asset(paths: ProjectPaths, path: string): Promise<BuildAsset> {
  const bytes = await readFile(path);
  return { path: relative(paths.root, path), sha256: await sha256(bytes), bytes: bytes.byteLength };
}
