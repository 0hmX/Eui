import type {PreparedRenderPlan, Renderer} from "@eui/renderer";

export interface ManimRenderPlan {
  readonly engine: "manim";
  readonly fps: number;
  readonly durationFrames: number;
  readonly prepared: PreparedRenderPlan;
}

/** Validates and seals the renderer-independent input passed to the Manim adapter. */
export class ManimRenderer implements Renderer<ManimRenderPlan> {
  readonly name = "manim";

  render(plan: PreparedRenderPlan): ManimRenderPlan {
    for (const tool of plan.tools) {
      if (!["text", "media.image", "captions", "code"].includes(tool.visual.kind)) {
        throw new Error(`Manim does not support prepared visual '${tool.visual.kind}'`);
      }
      if (tool.visual.kind === "media.image") {
        const source = (tool.visual.data as {asset?: {source?: unknown}}).asset?.source;
        if (typeof source === "string" && /^(?:https?:)?\/\//i.test(source)) {
          throw new Error(`Manim render input '${tool.id}' contains a network asset`);
        }
      }
    }
    return {engine: "manim", fps: plan.fps, durationFrames: plan.durationFrames, prepared: plan};
  }
}
