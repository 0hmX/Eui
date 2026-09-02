import { z } from "zod";

const hash = z.string().regex(/^[a-f0-9]{64}$/);
const artifact = z.object({
  file: z.string().regex(/^audio\.[A-Za-z0-9]+$/),
  sha256: hash,
  bytes: z.number().int().nonnegative(),
  mediaType: z.string().min(1),
  sampleRate: z.number().int().positive().optional(),
}).strict();

export const audioCacheManifestSchema = z.object({
  version: z.literal("1"),
  kind: z.literal("eui.audio"),
  synthesisKey: hash,
  narrationHash: hash,
  provider: z.object({ id: z.string().min(1), version: z.string().min(1) }).strict(),
  voiceReferenceHash: hash.nullable(),
  artifact,
}).strict();

const word = z.object({
  token: z.string().min(1),
  startMs: z.number().int().nonnegative(),
  endMs: z.number().int().nonnegative(),
}).strict().refine((item) => item.endMs >= item.startMs);
const durationMs = z.number().int().nonnegative();
const words = z.array(word);

export const alignmentResultSchema = z.object({
  durationMs,
  words,
}).strict().superRefine((result, context) => {
  result.words.forEach((item, index) => {
    if (item.endMs > result.durationMs) {
      context.addIssue({ code: "custom", path: ["words", index, "endMs"], message: "word ends after audio duration" });
    }
    if (index > 0 && item.startMs < result.words[index - 1]!.endMs) {
      context.addIssue({ code: "custom", path: ["words", index, "startMs"], message: "word timings overlap or are out of order" });
    }
  });
});

export const alignmentCacheManifestSchema = z.object({
  version: z.literal("1"),
  kind: z.literal("eui.alignment"),
  alignmentKey: hash,
  synthesisKey: hash,
  audioSha256: hash,
  aligner: z.object({ id: z.string().min(1), version: z.string().min(1) }).strict(),
  durationMs,
  words,
}).strict().superRefine((manifest, context) => {
  const result = alignmentResultSchema.safeParse({ durationMs: manifest.durationMs, words: manifest.words });
  if (!result.success) {
    result.error.issues.forEach((issue) => context.addIssue({ ...issue, path: issue.path }));
  }
});

export type AudioCacheManifest = z.infer<typeof audioCacheManifestSchema>;
export type AlignmentCacheManifest = z.infer<typeof alignmentCacheManifestSchema>;
