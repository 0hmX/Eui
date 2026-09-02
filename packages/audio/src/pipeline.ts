import { parseNarration, validateVideoPlan } from "@eui/compiler";
import type { VideoPlan, VoiceConfiguration } from "@eui/schema";
import { resolve } from "node:path";
import { hashFile, lookupAlignment, lookupAudio, writeAlignmentAtomically, writeAudioAtomically } from "./cache";
import { mapCuesToTimestamps } from "./cues";
import { hashNarration, normalizeNarration, stableCacheKey } from "./hash";
import type { AudioAligner, AudioBuildResult, AudioProvider, SceneAudioResult, VoiceReference } from "./types";

export interface BuildAudioOptions {
  cacheDirectory: string;
  providers: Readonly<Record<string, AudioProvider>>;
  aligner: AudioAligner;
  seed?: number;
  /** Voice-reference files keyed by VoiceConfiguration.voice. */
  voiceReferences?: Readonly<Record<string, string>>;
}

export async function buildAudio(input: unknown, options: BuildAudioOptions): Promise<AudioBuildResult> {
  const plan = validateVideoPlan(input);
  const seed = options.seed ?? 0;
  if (!Number.isSafeInteger(seed)) throw new TypeError("audio seed must be a safe integer");
  const scenes: SceneAudioResult[] = [];
  for (const scene of plan.scenes) {
    const voice = resolveVoice(plan, scene.narration);
    const provider = options.providers[voice.provider];
    if (!provider) throw new Error(`no audio provider registered for '${voice.provider}'`);
    if (provider.id !== voice.provider) throw new Error(`provider '${voice.provider}' reports id '${provider.id}'`);
    const authored = typeof scene.narration === "string" ? scene.narration : scene.narration.text;
    const parsed = parseNarration(authored);
    const text = normalizeNarration(parsed.text);
    const cues = parsed.cues;
    const narrationHash = await hashNarration(text);
    const voiceReference = await resolveVoiceReference(voice, options.voiceReferences);
    const synthesisKey = await stableCacheKey("eui.audio.synthesis.v1", {
      narrationHash,
      provider: { id: provider.id, version: provider.version },
      voice,
      voiceReferenceHash: voiceReference?.sha256 ?? null,
      seed,
    });

    let cachedAudio = await lookupAudio(options.cacheDirectory, synthesisKey);
    const audioCacheHit = cachedAudio !== undefined;
    if (!cachedAudio) {
      const generated = await provider.synthesize({ text, voice, seed, ...(voiceReference ? { voiceReference } : {}) });
      cachedAudio = await writeAudioAtomically(options.cacheDirectory, {
        version: "1",
        kind: "eui.audio",
        synthesisKey,
        narrationHash,
        provider: { id: provider.id, version: provider.version },
        voiceReferenceHash: voiceReference?.sha256 ?? null,
      }, generated);
    }

    const alignmentKey = await stableCacheKey("eui.audio.alignment.v1", {
      synthesisKey,
      audioSha256: cachedAudio.artifact.sha256,
      aligner: { id: options.aligner.id, version: options.aligner.version },
      tokens: parsed.tokens,
    });
    let alignment = await lookupAlignment(options.cacheDirectory, alignmentKey);
    const alignmentCacheHit = alignment !== undefined;
    if (!alignment) {
      const generated = await options.aligner.align({
        audio: cachedAudio.bytes,
        audioSha256: cachedAudio.artifact.sha256,
        text,
        tokens: parsed.tokens,
        mediaType: cachedAudio.artifact.mediaType,
      });
      // Reject incompatible timing before it can become a committed cache entry.
      mapCuesToTimestamps(text, cues, generated.words, generated.durationMs);
      alignment = await writeAlignmentAtomically(options.cacheDirectory, {
        version: "1",
        kind: "eui.alignment",
        alignmentKey,
        synthesisKey,
        audioSha256: cachedAudio.artifact.sha256,
        aligner: { id: options.aligner.id, version: options.aligner.version },
        durationMs: generated.durationMs,
        words: generated.words,
      });
    }
    scenes.push({
      sceneId: scene.id,
      narrationHash,
      synthesisKey,
      alignmentKey,
      audio: cachedAudio.artifact,
      durationMs: alignment.durationMs,
      words: alignment.words,
      cueTimesMs: mapCuesToTimestamps(text, cues, alignment.words, alignment.durationMs),
      audioCacheHit,
      alignmentCacheHit,
    });
  }
  return { version: "1", scenes };
}

function resolveVoice(plan: VideoPlan, narration: VideoPlan["scenes"][number]["narration"]): VoiceConfiguration {
  const voice = typeof narration === "string" ? plan.voice : narration.voice ?? plan.voice;
  if (!voice) throw new Error("narration has no voice configuration and the plan has no default voice");
  return voice;
}

async function resolveVoiceReference(
  voice: VoiceConfiguration,
  references: Readonly<Record<string, string>> | undefined,
): Promise<VoiceReference | undefined> {
  const path = references?.[voice.voice];
  if (!path) return undefined;
  const absolutePath = resolve(path);
  return { path: absolutePath, sha256: await hashFile(absolutePath) };
}
