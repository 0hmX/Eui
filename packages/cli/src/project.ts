import { validateVideoPlan } from "@eui/compiler";
import type { VideoPlan } from "@eui/schema";
import { readFile, stat } from "node:fs/promises";
import { basename, join, resolve } from "node:path";
import { pathToFileURL } from "node:url";
import type { ProjectPaths } from "./types";

const candidates = ["eui.ts", "eui.json"];

export async function resolveProject(input: string): Promise<ProjectPaths> {
  const target = resolve(input);
  let root: string;
  let source: string;
  const info = await stat(target).catch(() => undefined);
  if (info?.isFile()) {
    root = resolve(target, "..");
    source = target;
  } else if (info?.isDirectory()) {
    root = target;
    const found = await Promise.all(candidates.map(async (name) => ({ name, exists: await stat(join(root, name)).then((s) => s.isFile()).catch(() => false) })));
    const selected = found.find((item) => item.exists);
    if (!selected) throw new Error(`project '${target}' has no ${candidates.join(" or ")}`);
    source = join(root, selected.name);
  } else {
    throw new Error(`project does not exist: ${target}`);
  }
  const stateDirectory = join(root, ".eui", "build");
  const outputDirectory = join(root, "dist");
  return {
    root, source, stateDirectory, outputDirectory,
    cacheDirectory: join(root, ".eui", "cache"),
    graph: join(stateDirectory, "graph.json"),
    audioBuild: join(stateDirectory, "audio.json"),
    preparedPlan: join(stateDirectory, "prepared-plan.json"),
    framePlan: join(stateDirectory, "manim-plan.json"),
    narration: join(outputDirectory, "narration.wav"),
    videoOnly: join(stateDirectory, "video-only.mp4"),
    video: join(outputDirectory, "video.mp4"),
    srt: join(outputDirectory, "captions.srt"),
    vtt: join(outputDirectory, "captions.vtt"),
    manifest: join(outputDirectory, "manifest.json"),
  };
}

export async function loadProject(paths: ProjectPaths): Promise<VideoPlan> {
  let input: unknown;
  if (paths.source.endsWith(".json")) {
    input = JSON.parse(await readFile(paths.source, "utf8"));
  } else {
    const module = await import(`${pathToFileURL(paths.source).href}?eui=${Date.now()}`) as Record<string, unknown>;
    input = module.default ?? module.video ?? module.plan;
    if (input === undefined) throw new Error(`${basename(paths.source)} must export a default video plan`);
  }
  return validateVideoPlan(input);
}
