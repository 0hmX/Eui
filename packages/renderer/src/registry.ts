import type {CompiledTimeline} from "@eui/compiler";
import type {
  AssetLoader,
  CodeTokenizer,
  PreparedRenderPlan,
  PreparedToolInvocation,
  VisualTool,
} from "./types";

export interface PreparationServices {
  tokenizer: CodeTokenizer;
  assetLoader: AssetLoader;
}

export class ToolRegistryError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ToolRegistryError";
  }
}

export class ToolRegistry {
  readonly #tools = new Map<string, VisualTool>();

  constructor(tools: readonly VisualTool[] = []) {
    for (const tool of tools) this.register(tool);
  }

  register(tool: VisualTool): this {
    if (this.#tools.has(tool.name)) throw new ToolRegistryError(`duplicate visual tool '${tool.name}'`);
    this.#tools.set(tool.name, tool);
    return this;
  }

  resolve(name: string): VisualTool {
    const tool = this.#tools.get(name);
    if (!tool) throw new ToolRegistryError(`missing visual tool '${name}'`);
    return tool;
  }

  assertTimelineSupported(timeline: CompiledTimeline): void {
    const missing = [...new Set(timeline.scenes.flatMap((scene) => scene.tools.map((tool) => tool.tool)))]
      .filter((name) => !this.#tools.has(name))
      .sort();
    if (missing.length > 0) {
      throw new ToolRegistryError(`missing visual tools: ${missing.map((name) => `'${name}'`).join(", ")}`);
    }
  }

  async prepare(timeline: CompiledTimeline, services: PreparationServices): Promise<PreparedRenderPlan> {
    // Resolve the entire timeline before any expensive work starts.
    this.assertTimelineSupported(timeline);
    const prepared: PreparedToolInvocation[] = [];
    for (const scene of timeline.scenes) {
      for (const invocation of scene.tools) {
        const tool = this.resolve(invocation.tool);
        const parsed = tool.inputSchema.safeParse(invocation.input);
        if (!parsed.success) {
          const details = parsed.error.issues
            .map((issue) => `${issue.path.length ? issue.path.join(".") : "$"}: ${issue.message}`)
            .join("; ");
          throw new ToolRegistryError(`invalid input for '${invocation.tool}' (${invocation.id}): ${details}`);
        }
        const visual = await tool.prepare(parsed.data, {
          timeline,
          scene,
          invocation,
          tokenizer: services.tokenizer,
          assetLoader: services.assetLoader,
        });
        prepared.push({
          id: invocation.id,
          tool: invocation.tool,
          sceneId: scene.id,
          startFrame: invocation.startFrame,
          endFrame: invocation.endFrame,
          visual,
        });
      }
    }
    return {fps: timeline.fps, durationFrames: timeline.durationFrames, tools: prepared};
  }
}
