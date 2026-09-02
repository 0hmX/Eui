import type {CompiledScene, CompiledTimeline, CompiledToolInvocation} from "@eui/compiler";
import type {z} from "zod";

export interface PreparedToken {
  content: string;
  color: string;
  fontStyle?: number;
}

export type PreparedCodeLine = readonly PreparedToken[];

export interface CodeTokenizer {
  tokenize(code: string, language: string, theme: string): Promise<readonly PreparedCodeLine[]>;
}

export interface PreparedAsset {
  source: string;
  mimeType?: string;
  width?: number;
  height?: number;
}

/** Asset access is deliberately preparation-only; renderers receive PreparedAsset data. */
export interface AssetLoader {
  load(source: string): Promise<PreparedAsset>;
}

export interface ToolPreparationContext {
  timeline: CompiledTimeline;
  scene: CompiledScene;
  invocation: CompiledToolInvocation;
  tokenizer: CodeTokenizer;
  assetLoader: AssetLoader;
}

export interface PreparedVisual<K extends string = string, D = unknown> {
  kind: K;
  data: D;
}

export interface VisualTool<Input = unknown, Prepared extends PreparedVisual = PreparedVisual> {
  readonly name: string;
  readonly inputSchema: z.ZodType<Input, z.ZodTypeDef, unknown>;
  prepare(input: Input, context: ToolPreparationContext): Promise<Prepared> | Prepared;
}

export interface PreparedToolInvocation {
  id: string;
  tool: string;
  sceneId: string;
  startFrame: number;
  endFrame: number;
  visual: PreparedVisual;
}

export interface PreparedRenderPlan {
  fps: number;
  durationFrames: number;
  tools: readonly PreparedToolInvocation[];
}

/** Renderer implementations live in adapter packages, never in core or schema. */
export interface Renderer<Result> {
  readonly name: string;
  render(plan: PreparedRenderPlan): Result | Promise<Result>;
}
