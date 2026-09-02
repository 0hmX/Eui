import { parseNarration, validateVideoPlan } from "@eui/compiler";
import { stat } from "node:fs/promises";
import { contentKey, readGraph } from "./graph";
import { loadProject, resolveProject } from "./project";
import { stageNames, type StageInspection } from "./types";

export interface ProjectInspection {
  project: string;
  source: string;
  planKey: string;
  scenes: Array<{ id: string; narration: string; cues: Array<{ name: string; tokenOffset: number }>; durationMs?: number; resolvedCueMs?: Record<string, number> }>;
  stages: StageInspection[];
  outputs: { video: string; narration: string; srt: string; vtt: string; manifest: string };
}

/** Read-only: this never calls providers, aligners, renderers, or encoders. */
export async function inspectProject(project: string): Promise<ProjectInspection> {
  const paths = await resolveProject(project);
  const plan = validateVideoPlan(await loadProject(paths));
  const graph = await readGraph(paths);
  const planKey = await contentKey("eui.stage.validate.v1", plan);
  const audioInputsKey = await contentKey("eui.stage.audio-inputs.v1", {
    voice: plan.voice,
    scenes: plan.scenes.map((scene) => ({ id: scene.id, narration: scene.narration })),
  });
  const durations = graph.stages.alignment?.details?.durationsMs as Record<string, number> | undefined;
  const cueTimes = graph.stages.alignment?.details?.cuesMs as Record<string, Record<string, number>> | undefined;
  const scenes = plan.scenes.map((scene) => {
    const parsed = parseNarration(typeof scene.narration === "string" ? scene.narration : scene.narration.text);
    return {
      id: scene.id, narration: parsed.text,
      cues: parsed.cues.map(({ name, tokenOffset }) => ({ name, tokenOffset })),
      ...(durations?.[scene.id] === undefined ? {} : { durationMs: durations[scene.id] }),
      ...(cueTimes?.[scene.id] === undefined ? {} : { resolvedCueMs: cueTimes[scene.id] }),
    };
  });
  const stages: StageInspection[] = [];
  const stateByStage = new Map<string, StageInspection["state"]>();
  for (const stage of stageNames) {
    const record = graph.stages[stage];
    if (!record) {
      stages.push({ stage, state: "missing", reason: "stage has not completed", artifacts: [] });
      stateByStage.set(stage, "missing");
      continue;
    }
    const missing = (await Promise.all(record.artifacts.map(async (path) => await stat(path).then(() => undefined).catch(() => path))))
      .filter((path): path is string => path !== undefined);
    const planChanged = stage === "validate" && record.key !== planKey;
    const staleDependency = Object.entries(record.dependencies).find(([dependency, key]) => {
      if (stage === "audio" && dependency === "validate" && record.details?.audioInputsKey === audioInputsKey) return false;
      return graph.stages[dependency as keyof typeof graph.stages]?.key !== key || stateByStage.get(dependency) !== "fresh";
    })?.[0];
    const state = missing.length > 0 || planChanged || staleDependency !== undefined ? "stale" : "fresh";
    const reason = missing.length > 0
      ? `missing artifact${missing.length === 1 ? "" : "s"}: ${missing.join(", ")}`
      : planChanged ? "validated project content changed"
      : staleDependency ? `dependency '${staleDependency}' is stale or has a different cache key`
      : "cache key and artifacts match";
    stages.push({
      stage, key: record.key, state, reason, artifacts: record.artifacts,
      ...(record.details ? { details: record.details } : {}),
    });
    stateByStage.set(stage, state);
  }
  return {
    project: paths.root, source: paths.source, planKey, scenes, stages,
    outputs: { video: paths.video, narration: paths.narration, srt: paths.srt, vtt: paths.vtt, manifest: paths.manifest },
  };
}
