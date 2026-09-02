import { mkdir, readFile, rm } from "node:fs/promises";
import { join, resolve } from "node:path";
import { z } from "zod";
import type { AudioProvider, SynthesisRequest, SynthesisResult } from "./types";

const workerResponseSchema = z.discriminatedUnion("ok", [
  z.object({
    protocol: z.literal("eui.chatterbox"), version: z.literal(1), id: z.string().min(1), ok: z.literal(true),
    result: z.object({ sampleRate: z.number().int().positive() }).strict(),
  }).strict(),
  z.object({
    protocol: z.literal("eui.chatterbox"), version: z.literal(1), id: z.string().nullable(), ok: z.literal(false),
    error: z.object({ message: z.string().min(1), type: z.string().min(1).optional() }).strict(),
  }).strict(),
]);

export interface ChatterboxProviderOptions {
  python?: string;
  repositoryRoot?: string;
  device?: "auto" | "cpu" | "cuda" | "mps";
}

export class ChatterboxProvider implements AudioProvider {
  readonly id = "chatterbox";
  readonly version = "worker-v1";
  private readonly python: string;
  private readonly root: string;
  private readonly device: "auto" | "cpu" | "cuda" | "mps";

  constructor(options: ChatterboxProviderOptions = {}) {
    this.python = options.python ?? "python3";
    this.root = resolve(options.repositoryRoot ?? process.cwd());
    this.device = options.device ?? "auto";
  }

  async synthesize(request: SynthesisRequest): Promise<SynthesisResult> {
    const temporary = join(this.root, ".eui-cache", ".worker", crypto.randomUUID());
    const outputPath = join(temporary, "audio.wav");
    await mkdir(temporary, { recursive: true });
    try {
      const child = Bun.spawn({
        cmd: [this.python, join(this.root, "workers", "chatterbox", "worker.py")],
        cwd: this.root,
        stdin: "pipe",
        stdout: "pipe",
        stderr: "pipe",
        env: { ...process.env, PYTHONPATH: join(this.root, "submodule", "chatterbox", "src") },
      });
      const id = crypto.randomUUID();
      // Narration is encoded only as JSON on stdin; it is never part of a command or shell source.
      child.stdin.write(`${JSON.stringify({
        protocol: "eui.chatterbox",
        version: 1,
        id,
        method: "synthesize",
        params: {
          text: request.text,
          outputPath,
          seed: request.seed,
          device: this.device,
          voiceReferencePath: request.voiceReference?.path ?? null,
          options: request.voice.options ?? {},
        },
      })}\n`);
      child.stdin.end();
      const [exitCode, stdout, stderr] = await Promise.all([
        child.exited,
        new Response(child.stdout).text(),
        new Response(child.stderr).text(),
      ]);
      const lines = stdout.split(/\r?\n/u).filter((line) => line.trim() !== "");
      if (lines.length !== 1) throw new Error(`Chatterbox worker returned ${lines.length} protocol messages; expected 1`);
      let decoded: unknown;
      try { decoded = JSON.parse(lines[0]!); }
      catch { throw new Error("Chatterbox worker returned invalid JSON"); }
      const parsed = workerResponseSchema.safeParse(decoded);
      if (!parsed.success) throw new Error(`Chatterbox worker returned an invalid response: ${parsed.error.issues[0]?.message ?? "unknown error"}`);
      const response = parsed.data;
      if (response.id !== id) throw new Error("Chatterbox worker response id did not match the request");
      if (!response.ok) throw new Error(response.error.message);
      if (exitCode !== 0) throw new Error(stderr.trim() || `Chatterbox worker exited with code ${exitCode}`);
      return {
        audio: await readFile(outputPath),
        extension: "wav",
        mediaType: "audio/wav",
        sampleRate: response.result.sampleRate,
      };
    } finally {
      await rm(temporary, { recursive: true, force: true });
    }
  }
}
