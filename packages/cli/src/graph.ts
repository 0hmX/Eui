import { sha256, stableJson } from "@eui/audio";
import { mkdir, readFile, stat, writeFile } from "node:fs/promises";
import { dirname } from "node:path";
import type { BuildGraph, ProjectPaths, StageName, StageRecord } from "./types";

export async function contentKey(namespace: string, input: unknown): Promise<string> {
  return sha256(`${namespace}\0${stableJson(input as never)}`);
}

export async function readGraph(paths: ProjectPaths): Promise<BuildGraph> {
  try {
    return JSON.parse(await readFile(paths.graph, "utf8")) as BuildGraph;
  } catch {
    return { version: "1", project: paths.root, stages: {} };
  }
}

export async function writeGraph(paths: ProjectPaths, graph: BuildGraph): Promise<void> {
  await mkdir(dirname(paths.graph), { recursive: true });
  await writeFile(paths.graph, `${stableJson(graph as never)}\n`);
}

export async function artifactExists(path: string): Promise<boolean> {
  return stat(path).then((value) => value.isFile()).catch(() => false);
}

export async function isFresh(record: StageRecord | undefined, key: string): Promise<boolean> {
  return record?.key === key && (await Promise.all(record.artifacts.map(artifactExists))).every(Boolean);
}

export async function recordStage(
  graph: BuildGraph,
  stage: StageName,
  key: string,
  dependencies: StageRecord["dependencies"],
  artifacts: string[],
  details?: Record<string, unknown>,
): Promise<void> {
  graph.stages[stage] = {
    key, dependencies, artifacts,
    completedAt: new Date().toISOString(),
    ...(details ? { details } : {}),
  };
}
