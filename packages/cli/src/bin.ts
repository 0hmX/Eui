#!/usr/bin/env bun
import { defaultServices } from "./adapters";
import { inspectProject } from "./inspect";
import { prepareProject, renderProject, validateProject, buildVoice } from "./pipeline";

const usage = `Eui 2\n\nUsage:\n  eui validate <project> [--json]\n  eui voice <project> [--json]\n  eui preview <project> [--json]\n  eui render <project> [--json]\n  eui inspect <project> [--json]\n  eui doctor [--json]`;

export async function runCli(argv: string[], io = { log: console.log, error: console.error }): Promise<number> {
  const json = argv.includes("--json");
  const args = argv.filter((arg) => arg !== "--json");
  const [command, project] = args;
  try {
    if (!command) {
      if (json) io.error(JSON.stringify({ ok: false, error: "missing command", usage }));
      else io.log(usage);
      return 2;
    }
    if (command === "help" || command === "--help" || command === "-h") {
      emit(io, json, { ok: true, usage }, usage);
      return 0;
    }
    const projectCommands = new Set(["validate", "voice", "preview", "render", "inspect"]);
    if (command !== "doctor" && !projectCommands.has(command)) throw new UsageError(`unknown command '${command}'`);
    if (args.length > (command === "doctor" ? 1 : 2)) throw new UsageError(`unexpected argument '${args.at(-1)}'`);
    if (command === "doctor") {
      const checks = await doctor();
      const ok = checks.every((check) => check.ok || !check.required);
      emit(io, json, { ok, checks }, checks.map((check) => `${check.ok ? "ok" : "missing"} ${check.name}: ${check.detail}`).join("\n"));
      return ok ? 0 : 1;
    }
    if (!project) throw new UsageError(`${command} requires a <project>`);
    if (command === "validate") {
      const result = await validateProject(project);
      emit(io, json, { ok: true, command, project: result.paths.root, cacheKey: result.key }, `valid: ${result.paths.source}`);
      return 0;
    }
    if (command === "inspect") {
      const result = await inspectProject(project);
      emit(io, json, result, formatInspection(result));
      return 0;
    }
    const services = defaultServices();
    if (command === "voice") {
      const result = await buildVoice(project, services);
      emit(io, json, { ok: true, command, narration: result.paths.narration, scenes: result.audio.scenes }, `narration: ${result.paths.narration}`);
      return 0;
    }
    if (command === "preview") {
      const result = await prepareProject(project, services);
      emit(io, json, { ok: true, command, preparedPlan: result.paths.preparedPlan, durationFrames: result.timeline.durationFrames }, `prepared plan: ${result.paths.preparedPlan}`);
      return 0;
    }
    if (command === "render") {
      const paths = await renderProject(project, services);
      const outputs = { video: paths.video, narration: paths.narration, srt: paths.srt, vtt: paths.vtt, manifest: paths.manifest };
      emit(io, json, { ok: true, command, outputs }, Object.entries(outputs).map(([kind, path]) => `${kind}: ${path}`).join("\n"));
      return 0;
    }
    throw new UsageError(`unknown command '${command}'`);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    if (json) io.error(JSON.stringify({ ok: false, error: message })); else io.error(`error: ${message}`);
    return error instanceof UsageError ? 2 : 1;
  }
}

class UsageError extends Error {}
function emit(io: { log(value: string): void }, json: boolean, value: unknown, text: string): void { io.log(json ? JSON.stringify(value) : text); }
function formatInspection(value: Awaited<ReturnType<typeof inspectProject>>): string {
  const scenes = value.scenes.map((scene) => `${scene.id}: ${scene.durationMs ?? "unknown"}ms; cues ${JSON.stringify(scene.resolvedCueMs ?? scene.cues)}`);
  const stages = value.stages.map((stage) => `${stage.stage}: ${stage.state} (${stage.reason})${stage.key ? ` key=${stage.key}` : ""}${stage.details ? ` details=${JSON.stringify(stage.details)}` : ""}`);
  return [...scenes, ...stages, `outputs: ${JSON.stringify(value.outputs)}`].join("\n");
}
async function doctor(): Promise<Array<{ name: string; ok: boolean; required: boolean; detail: string }>> {
  const executable = async (name: string, command: string, required: boolean) => {
    const child = Bun.spawn(["which", command], { stdout: "pipe", stderr: "ignore" });
    const [exit, output] = await Promise.all([child.exited, new Response(child.stdout).text()]);
    return { name, ok: exit === 0, required, detail: exit === 0 ? output.trim() : `${command} not found` };
  };
  return Promise.all([
    executable("Bun", "bun", true), executable("Python", "python3", true), executable("FFmpeg", process.env.EUI_FFMPEG ?? "ffmpeg", false),
    executable("alignment adapter", process.env.EUI_ALIGN_COMMAND ?? "eui-align", false),
    executable("render adapter", process.env.EUI_RENDER_COMMAND ?? "eui-manim-render", false),
  ]);
}

if (import.meta.main) process.exitCode = await runCli(Bun.argv.slice(2));
