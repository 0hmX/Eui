import { sha256, stableJson } from "./hash";
import type { AlignmentRequest, AlignmentResult, AudioAligner, AudioProvider, SynthesisRequest, SynthesisResult } from "./types";

export class FakeAudioProvider implements AudioProvider {
  readonly id: string;
  readonly version: string;
  calls: SynthesisRequest[] = [];

  constructor(id = "fake", version = "1") {
    this.id = id;
    this.version = version;
  }

  async synthesize(request: SynthesisRequest): Promise<SynthesisResult> {
    this.calls.push(request);
    const payload = stableJson({
      text: request.text,
      voice: request.voice,
      seed: request.seed,
      voiceReferenceHash: request.voiceReference?.sha256 ?? null,
    });
    return { audio: new TextEncoder().encode(`FAKE-WAV\n${await sha256(payload)}\n`), extension: "wav", mediaType: "audio/wav", sampleRate: 24_000 };
  }
}

export class FakeAudioAligner implements AudioAligner {
  readonly id: string;
  readonly version: string;
  calls: AlignmentRequest[] = [];

  constructor(id = "fake", version = "1") {
    this.id = id;
    this.version = version;
  }

  async align(request: AlignmentRequest): Promise<AlignmentResult> {
    this.calls.push(request);
    const words = request.tokens.map((token, index) => ({ token, startMs: index * 200, endMs: index * 200 + 140 }));
    return { durationMs: words.length === 0 ? 0 : words.length * 200, words };
  }
}
