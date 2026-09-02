import type { VoiceConfiguration, WordTiming } from "@eui/schema";

export interface VoiceReference {
  /** A path passed to the provider. Cache identity is based on file bytes, not this path. */
  path: string;
  sha256: string;
}

export interface SynthesisRequest {
  text: string;
  voice: VoiceConfiguration;
  seed: number;
  voiceReference?: VoiceReference;
}

export interface SynthesisResult {
  audio: Uint8Array;
  extension: string;
  mediaType: string;
  sampleRate?: number;
}

export interface AudioProvider {
  readonly id: string;
  readonly version: string;
  synthesize(request: SynthesisRequest): Promise<SynthesisResult>;
}

export interface AlignmentRequest {
  audio: Uint8Array;
  audioSha256: string;
  text: string;
  tokens: readonly string[];
  mediaType: string;
}

export interface AlignmentResult {
  durationMs: number;
  words: WordTiming[];
}

export interface AudioAligner {
  readonly id: string;
  readonly version: string;
  align(request: AlignmentRequest): Promise<AlignmentResult>;
}

export interface AudioArtifact {
  path: string;
  sha256: string;
  bytes: number;
  mediaType: string;
  sampleRate?: number;
}

export interface SceneAudioResult {
  sceneId: string;
  narrationHash: string;
  synthesisKey: string;
  alignmentKey: string;
  audio: AudioArtifact;
  durationMs: number;
  words: WordTiming[];
  cueTimesMs: Record<string, number>;
  audioCacheHit: boolean;
  alignmentCacheHit: boolean;
}

export interface AudioBuildResult {
  version: "1";
  scenes: SceneAudioResult[];
}

export type StableValue = string | number | boolean | null | undefined | StableValue[] | { [key: string]: StableValue };
