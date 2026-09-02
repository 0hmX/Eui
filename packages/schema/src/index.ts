import { z } from "zod";

export type JsonPrimitive = string | number | boolean | null;
export type JsonValue = JsonPrimitive | JsonValue[] | { [key: string]: JsonValue };

export const jsonValueSchema: z.ZodType<JsonValue> = z.lazy(() =>
  z.union([
    z.string(),
    z.number().finite(),
    z.boolean(),
    z.null(),
    z.array(jsonValueSchema),
    z.record(z.string(), jsonValueSchema),
  ]),
);

const identifierSchema = z
  .string()
  .min(1)
  .regex(/^[A-Za-z][A-Za-z0-9_-]*$/, "must start with a letter and contain only letters, numbers, _ or -");

const toolNameSchema = z
  .string()
  .min(1)
  .regex(/^[A-Za-z][A-Za-z0-9_-]*(?:\.[A-Za-z][A-Za-z0-9_-]*)*$/, "must be a dot-separated tool name");

export const projectSettingsSchema = z
  .object({
    width: z.number().int().positive(),
    height: z.number().int().positive(),
    fps: z.number().int().positive().max(240),
    background: z.string().min(1).default("#000000"),
  })
  .strict();

export const voiceConfigurationSchema = z
  .object({
    provider: identifierSchema.default("chatterbox"),
    voice: z.string().min(1),
    language: z.string().min(2).optional(),
    speed: z.number().positive().default(1),
    options: z.record(z.string(), jsonValueSchema).optional(),
  })
  .strict();

export const narrationSchema = z
  .object({
    text: z.string().min(1),
    voice: voiceConfigurationSchema.optional(),
  })
  .strict();

export const cueMarkerSchema = z
  .object({
    name: identifierSchema,
    characterOffset: z.number().int().nonnegative(),
    tokenOffset: z.number().int().nonnegative(),
  })
  .strict();

export const timingAnchorSchema = z.discriminatedUnion("type", [
  z.object({ type: z.literal("scene-start"), offsetMs: z.number().int().default(0) }).strict(),
  z.object({ type: z.literal("scene-end"), offsetMs: z.number().int().default(0) }).strict(),
  z.object({ type: z.literal("cue"), cue: identifierSchema, offsetMs: z.number().int().default(0) }).strict(),
]);

export const layerSchema = z
  .object({
    id: identifierSchema,
    type: identifierSchema,
    props: z.record(z.string(), jsonValueSchema).default({}),
    from: timingAnchorSchema.optional(),
    to: timingAnchorSchema.optional(),
  })
  .strict();

export const toolInvocationSchema = z
  .object({
    id: identifierSchema,
    tool: toolNameSchema,
    at: timingAnchorSchema,
    until: timingAnchorSchema.optional(),
    input: z.record(z.string(), jsonValueSchema).default({}),
  })
  .strict();

export const sceneSchema = z
  .object({
    id: identifierSchema,
    narration: z.union([z.string().min(1), narrationSchema]),
    layers: z.array(layerSchema).default([]),
    tools: z.array(toolInvocationSchema).default([]),
  })
  .strict()
  .superRefine((scene, context) => {
    for (const [collectionName, collection] of [["layers", scene.layers], ["tools", scene.tools]] as const) {
      const seen = new Set<string>();
      collection.forEach((item, index) => {
        if (seen.has(item.id)) {
          context.addIssue({
            code: "custom",
            path: [collectionName, index, "id"],
            message: `duplicate ${collectionName === "layers" ? "layer" : "tool"} id '${item.id}'`,
          });
        }
        seen.add(item.id);
      });
    }
  });

export const videoPlanSchema = z
  .object({
    version: z.literal("2"),
    settings: projectSettingsSchema,
    voice: voiceConfigurationSchema.optional(),
    scenes: z.array(sceneSchema).min(1),
  })
  .strict()
  .superRefine((plan, context) => {
    const seen = new Set<string>();
    plan.scenes.forEach((scene, index) => {
      if (seen.has(scene.id)) {
        context.addIssue({ code: "custom", path: ["scenes", index, "id"], message: `duplicate scene id '${scene.id}'` });
      }
      seen.add(scene.id);
    });
  });

export const wordTimingSchema = z
  .object({
    token: z.string().min(1),
    startMs: z.number().int().nonnegative(),
    endMs: z.number().int().nonnegative(),
  })
  .strict()
  .refine((word) => word.endMs >= word.startMs, { message: "endMs must be greater than or equal to startMs", path: ["endMs"] });

export const narrationAlignmentSchema = z
  .object({
    sceneId: identifierSchema,
    durationMs: z.number().int().nonnegative(),
    words: z.array(wordTimingSchema),
  })
  .strict();

export const buildAssetSchema = z
  .object({
    path: z.string().min(1),
    sha256: z.string().regex(/^[a-f0-9]{64}$/),
    bytes: z.number().int().nonnegative(),
  })
  .strict();

export const buildManifestSchema = z
  .object({
    version: z.literal("1"),
    planHash: z.string().regex(/^[a-f0-9]{64}$/),
    audio: z.record(z.string(), buildAssetSchema),
    outputs: z.array(buildAssetSchema).default([]),
  })
  .strict();

export type ProjectSettings = z.infer<typeof projectSettingsSchema>;
export type VoiceConfiguration = z.infer<typeof voiceConfigurationSchema>;
export type Narration = z.infer<typeof narrationSchema>;
export type CueMarker = z.infer<typeof cueMarkerSchema>;
export type TimingAnchor = z.infer<typeof timingAnchorSchema>;
export type Layer = z.infer<typeof layerSchema>;
export type ToolInvocation = z.infer<typeof toolInvocationSchema>;
export type Scene = z.infer<typeof sceneSchema>;
export type VideoPlan = z.infer<typeof videoPlanSchema>;
export type WordTiming = z.infer<typeof wordTimingSchema>;
export type NarrationAlignment = z.infer<typeof narrationAlignmentSchema>;
export type BuildAsset = z.infer<typeof buildAssetSchema>;
export type BuildManifest = z.infer<typeof buildManifestSchema>;
