import type { AudioAligner, AudioBuildResult, AudioProvider } from "@eui/audio";
import type { CompiledTimeline } from "@eui/compiler";
import type { PreparedRenderPlan } from "@eui/renderer";
import type { VideoPlan } from "@eui/schema";

export const stageNames = ["validate", "audio", "alignment", "prepare", "render", "mux", "captions", "manifest"] as const;
export type StageName = typeof stageNames[number];

export interface StageRecord {
  key: string;
  dependencies: Partial<Record<StageName, string>>;
  completedAt: string;
  artifacts: string[];
  details?: Record<string, unknown>;
}

export interface BuildGraph {
  version: "1";
  project: string;
  stages: Partial<Record<StageName, StageRecord>>;
}

export interface ProjectPaths {
  root: string;
  source: string;
  stateDirectory: string;
  cacheDirectory: string;
  outputDirectory: string;
  graph: string;
  audioBuild: string;
  preparedPlan: string;
  framePlan: string;
  narration: string;
  videoOnly: string;
  video: string;
  srt: string;
  vtt: string;
  manifest: string;
}

export interface EncodingAdapter {
  readonly id: string;
  readonly version: string;
  render(plan: PreparedRenderPlan, output: string): Promise<void>;
  concatenateAudio(inputs: readonly string[], output: string): Promise<void>;
  mux(video: string, narration: string, output: string): Promise<void>;
}

export interface BuildServices {
  providers: Readonly<Record<string, AudioProvider>>;
  aligner: AudioAligner;
  encoder: EncodingAdapter;
}

export interface PreEncodingPlan {
  plan: VideoPlan;
  audio: AudioBuildResult;
  timeline: CompiledTimeline;
  prepared: PreparedRenderPlan;
  paths: ProjectPaths;
}

export interface StageInspection {
  stage: StageName;
  key?: string;
  state: "missing" | "fresh" | "stale";
  reason: string;
  artifacts: string[];
  details?: Record<string, unknown>;
}
