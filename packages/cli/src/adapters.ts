import { ChatterboxProvider, alignmentResultSchema } from "@eui/audio";
import type { AudioAligner, AlignmentRequest, AlignmentResult } from "@eui/audio";
import type { PreparedRenderPlan } from "@eui/renderer";
import { copyFile, mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import type { BuildServices, EncodingAdapter } from "./types";

/** Alignment is kept behind an external JSON-lines adapter just like synthesis. */
export class CommandAligner implements AudioAligner {
  readonly id = "eui-aligner";
  readonly version = "command-v1";
  constructor(private readonly command = process.env.EUI_ALIGN_COMMAND ?? "eui-align") {}

  async align(request: AlignmentRequest): Promise<AlignmentResult> {
    const id = crypto.randomUUID();
    const child = Bun.spawn([this.command], { stdin: "pipe", stdout: "pipe", stderr: "pipe" });
    child.stdin.write(`${JSON.stringify({
      protocol: "eui.aligner",
      version: 1,
      id,
      method: "align",
      params: {
        text: request.text,
        tokens: request.tokens,
        audioSha256: request.audioSha256,
        mediaType: request.mediaType,
        audioBase64: base64(request.audio),
      },
    })}\n`);
    child.stdin.end();
    const [exit, stdout, stderr] = await Promise.all([child.exited, new Response(child.stdout).text(), new Response(child.stderr).text()]);
    if (exit !== 0) throw new Error(stderr.trim() || `${this.command} exited with code ${exit}`);
    let response: unknown;
    try { response = JSON.parse(stdout); }
    catch { throw new Error(`${this.command} returned invalid JSON`); }
    if (!isRecord(response)
      || response.protocol !== "eui.aligner"
      || response.version !== 1
      || response.id !== id
      || typeof response.ok !== "boolean") {
      throw new Error(`${this.command} returned an invalid protocol response`);
    }
    if (!response.ok) {
      const message = isRecord(response.error) && typeof response.error.message === "string" ? response.error.message : "alignment failed";
      throw new Error(message);
    }
    const parsed = alignmentResultSchema.safeParse(response.result);
    if (!parsed.success) throw new Error(`${this.command} returned invalid alignment data: ${parsed.error.issues[0]?.message ?? "unknown error"}`);
    return parsed.data;
  }
}

export class CommandEncodingAdapter implements EncodingAdapter {
  readonly id = "manim+ffmpeg";
  readonly version = "command-v1";
  constructor(
    private readonly renderCommand = process.env.EUI_RENDER_COMMAND ?? "eui-manim-render",
    private readonly ffmpeg = process.env.EUI_FFMPEG ?? "ffmpeg",
  ) {}

  async render(plan: PreparedRenderPlan, output: string): Promise<void> {
    await mkdir(dirname(output), { recursive: true });
    await run(this.renderCommand, ["--output", output], `${JSON.stringify(plan)}\n`);
  }

  async concatenateAudio(inputs: readonly string[], output: string): Promise<void> {
    await mkdir(dirname(output), { recursive: true });
    if (inputs.length === 1) { await copyFile(inputs[0]!, output); return; }
    if (inputs.length === 0) throw new Error("cannot assemble narration without scene audio");
    const inputArguments = inputs.flatMap((path) => ["-i", path]);
    await run(this.ffmpeg, [
      "-y", ...inputArguments,
      "-filter_complex", `concat=n=${inputs.length}:v=0:a=1[out]`,
      "-map", "[out]", "-c:a", "pcm_s16le", output,
    ]);
  }

  async mux(video: string, narration: string, output: string): Promise<void> {
    await mkdir(dirname(output), { recursive: true });
    await run(this.ffmpeg, ["-y", "-i", video, "-i", narration, "-c:v", "copy", "-c:a", "aac", "-shortest", output]);
  }
}

async function run(command: string, args: string[], stdin?: string): Promise<void> {
  const child = Bun.spawn([command, ...args], { stdin: stdin === undefined ? "ignore" : "pipe", stdout: "ignore", stderr: "pipe" });
  if (stdin !== undefined) { child.stdin.write(stdin); child.stdin.end(); }
  const [exit, stderr] = await Promise.all([child.exited, new Response(child.stderr).text()]);
  if (exit !== 0) throw new Error(stderr.trim() || `${command} exited with code ${exit}`);
}

export function defaultServices(repositoryRoot = resolve(dirname(fileURLToPath(import.meta.url)), "../../..")): BuildServices {
  return {
    providers: { chatterbox: new ChatterboxProvider({ repositoryRoot }) },
    aligner: new CommandAligner(),
    encoder: new CommandEncodingAdapter(),
  };
}

function base64(bytes: Uint8Array): string {
  let binary = "";
  for (let offset = 0; offset < bytes.length; offset += 0x8000) {
    binary += String.fromCharCode(...bytes.subarray(offset, offset + 0x8000));
  }
  return btoa(binary);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}
