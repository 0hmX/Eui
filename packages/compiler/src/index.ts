import {
  narrationAlignmentSchema,
  videoPlanSchema,
  type CueMarker,
  type NarrationAlignment,
  type TimingAnchor,
  type VideoPlan,
} from "@eui/schema";
import type { z } from "zod";

export interface CompilerIssue {
  path: (string | number)[];
  message: string;
}

export class CompileError extends Error {
  readonly issues: readonly CompilerIssue[];

  constructor(issues: readonly CompilerIssue[]) {
    super(issues.map((issue) => `${formatPath(issue.path)}: ${issue.message}`).join("\n"));
    this.name = "CompileError";
    this.issues = issues;
  }
}

export interface ParsedNarration {
  text: string;
  cues: CueMarker[];
  tokens: string[];
}

export interface FrameInterval {
  startFrame: number;
  endFrame: number;
}

export interface CompiledLayer extends FrameInterval {
  id: string;
  type: string;
  props: Record<string, import("@eui/schema").JsonValue>;
}

export interface CompiledWord extends FrameInterval {
  token: string;
}

export interface CompiledNarration extends ParsedNarration {
  words: CompiledWord[];
}

export interface CompiledToolInvocation extends FrameInterval {
  id: string;
  tool: string;
  /** @deprecated Use startFrame. Retained for compatibility with Stage 1 consumers. */
  frame: number;
  input: Record<string, import("@eui/schema").JsonValue>;
}

export interface CompiledScene extends FrameInterval {
  id: string;
  narration: CompiledNarration;
  durationMs: number;
  cues: Record<string, number>;
  layers: CompiledLayer[];
  tools: CompiledToolInvocation[];
}

export interface CompiledTimeline {
  fps: number;
  durationFrames: number;
  scenes: CompiledScene[];
}

const cueNamePattern = /^[A-Za-z][A-Za-z0-9_-]*$/;
const cueMarkerPattern = /\[\[cue:([\s\S]*?)\]\]/g;

export function parseNarration(source: string, path: (string | number)[] = ["narration"]): ParsedNarration {
  const rawParts: string[] = [];
  const rawCues: Array<{ name: string; offset: number }> = [];
  const issues: CompilerIssue[] = [];
  let sourceIndex = 0;
  let rawLength = 0;

  for (const match of source.matchAll(cueMarkerPattern)) {
    const index = match.index;
    const preceding = source.slice(sourceIndex, index);
    rawParts.push(preceding);
    rawLength += preceding.length;
    const name = match[1] ?? "";
    if (!cueNamePattern.test(name)) {
      issues.push({ path, message: `invalid cue name '${name}'` });
    } else {
      rawCues.push({ name, offset: rawLength });
    }
    sourceIndex = index + match[0].length;
  }
  rawParts.push(source.slice(sourceIndex));
  const rawText = rawParts.join("");

  if (rawText.includes("[[cue:")) {
    issues.push({ path, message: "malformed or unclosed cue marker" });
  }

  const duplicates = new Set<string>();
  const seen = new Set<string>();
  for (const marker of rawCues) {
    if (seen.has(marker.name)) duplicates.add(marker.name);
    seen.add(marker.name);
  }
  for (const name of duplicates) {
    issues.push({ path, message: `duplicate cue '${name}'` });
  }
  if (issues.length > 0) throw new CompileError(issues);

  const text = normalizeSpeech(rawText);
  const tokens = tokenize(text);
  const cues = rawCues.map(({ name, offset }) => {
    const prefix = normalizeSpeechPrefix(rawText.slice(0, offset));
    return {
      name,
      characterOffset: prefix.length,
      tokenOffset: tokenize(prefix).length,
    };
  });
  return { text, cues, tokens };
}

export function millisecondsToFrame(milliseconds: number, fps: number): number {
  if (!Number.isFinite(milliseconds) || milliseconds < 0) throw new RangeError("milliseconds must be finite and non-negative");
  if (!Number.isInteger(fps) || fps <= 0) throw new RangeError("fps must be a positive integer");
  return Math.floor((milliseconds * fps) / 1000 + 0.5);
}

export function millisecondsToFrameInterval(startMs: number, endMs: number, fps: number): FrameInterval {
  if (endMs < startMs) throw new RangeError("endMs must be greater than or equal to startMs");
  return { startFrame: millisecondsToFrame(startMs, fps), endFrame: millisecondsToFrame(endMs, fps) };
}

interface Lexeme { start: number; end: number; value: string }
const lexicalPattern = /[\p{L}\p{N}]+(?:['’][\p{L}\p{N}]+)*/gu;

function lexemes(value: string): Lexeme[] {
  return [...value.matchAll(lexicalPattern)].map((match) => ({
    start: match.index,
    end: match.index + match[0].length,
    value: match[0]!.normalize("NFKC").toLocaleLowerCase("en-US").replaceAll("’", "'"),
  }));
}

/** Resolves cue character boundaries against aligned words using half-open timing intervals. */
export function resolveCueTimestamps(
  text: string,
  cues: readonly CueMarker[],
  words: readonly import("@eui/schema").WordTiming[],
  durationMs: number,
): Record<string, number> {
  const source = lexemes(text);
  const aligned = words.flatMap((word, wordIndex) =>
    lexemes(word.token).map((item) => ({ value: item.value, wordIndex })),
  );
  if (source.length === 0) {
    return Object.fromEntries(cues.map((cue) => [
      cue.name,
      cue.tokenOffset >= words.length ? durationMs : words[cue.tokenOffset]!.startMs,
    ]));
  }
  if (source.length !== aligned.length) {
    throw new Error(`narration has ${source.length} lexical words but alignment has ${aligned.length}`);
  }
  source.forEach((item, index) => {
    if (item.value !== aligned[index]!.value) {
      throw new Error(`word ${index} is '${item.value}' in narration and '${aligned[index]!.value}' in alignment`);
    }
  });

  const result: Record<string, number> = {};
  for (const cue of cues) {
    const offset = Math.max(0, Math.min(text.length, cue.characterOffset));
    if (offset >= text.length) {
      result[cue.name] = durationMs;
      continue;
    }
    const nextIndex = source.findIndex((item) => offset <= item.end);
    if (nextIndex < 0) {
      result[cue.name] = durationMs;
      continue;
    }
    const next = source[nextIndex]!;
    if (offset <= next.start) {
      const previous = source[nextIndex - 1];
      const gap = previous ? text.slice(previous.end, offset) : "";
      const previousWordIndex = nextIndex > 0 ? aligned[nextIndex - 1]!.wordIndex : undefined;
      result[cue.name] = previous && previousWordIndex !== undefined && /[.!?…]/u.test(gap)
        ? words[previousWordIndex]!.endMs
        : words[aligned[nextIndex]!.wordIndex]!.startMs;
    } else if (offset < next.end) {
      result[cue.name] = words[aligned[nextIndex]!.wordIndex]!.startMs;
    } else {
      result[cue.name] = words[aligned[nextIndex]!.wordIndex]!.endMs;
    }
  }
  return result;
}

export function validateVideoPlan(input: unknown): VideoPlan {
  const result = videoPlanSchema.safeParse(input);
  if (!result.success) throw zodCompileError(result.error.issues);
  return result.data;
}

export function compileTimeline(input: unknown, alignmentInput: readonly unknown[]): CompiledTimeline {
  const plan = validateVideoPlan(input);
  const alignments = parseAlignments(alignmentInput);
  const issues: CompilerIssue[] = [];
  const alignmentByScene = new Map<string, { alignment: NarrationAlignment; inputIndex: number }>();

  alignments.forEach((alignment, index) => {
    if (alignmentByScene.has(alignment.sceneId)) {
      issues.push({ path: ["alignments", index, "sceneId"], message: `duplicate alignment for scene '${alignment.sceneId}'` });
    }
    alignmentByScene.set(alignment.sceneId, { alignment, inputIndex: index });
  });

  const sceneIds = new Set(plan.scenes.map((item) => item.id));
  alignments.forEach((alignment, index) => {
    if (!sceneIds.has(alignment.sceneId)) {
      issues.push({ path: ["alignments", index, "sceneId"], message: `unknown scene '${alignment.sceneId}'` });
    }
  });

  const parsed = plan.scenes.map((item, sceneIndex) => {
    const narrationText = typeof item.narration === "string" ? item.narration : item.narration.text;
    let narration: ParsedNarration | undefined;
    try {
      narration = parseNarration(narrationText, ["scenes", sceneIndex, "narration"]);
    } catch (error) {
      if (error instanceof CompileError) issues.push(...error.issues);
      else throw error;
    }
    const alignmentEntry = alignmentByScene.get(item.id);
    if (!alignmentEntry) {
      issues.push({ path: ["alignments"], message: `missing alignment for scene '${item.id}'` });
    }
    if (narration && alignmentEntry) {
      validateAlignment(narration, alignmentEntry.alignment, alignmentEntry.inputIndex, issues);
    }
    return { item, narration, alignment: alignmentEntry?.alignment, sceneIndex };
  });

  if (issues.length > 0) throw new CompileError(issues);

  let timelineFrame = 0;
  const scenes: CompiledScene[] = parsed.map(({ item, narration, alignment, sceneIndex }) => {
    // All absent values were reported above.
    const parsedNarration = narration!;
    const sceneAlignment = alignment!;
    const durationFrames = millisecondsToFrame(sceneAlignment.durationMs, plan.settings.fps);
    let cueTimes: Record<string, number> = {};
    try {
      cueTimes = resolveCueTimestamps(parsedNarration.text, parsedNarration.cues, sceneAlignment.words, sceneAlignment.durationMs);
    } catch (error) {
      issues.push({
        path: ["alignments", alignmentByScene.get(item.id)!.inputIndex, "words"],
        message: `cannot map narration cues: ${error instanceof Error ? error.message : String(error)}`,
      });
    }
    const cueFrames = new Map(Object.entries(cueTimes).map(([name, localMs]) => [
      name,
      millisecondsToFrame(localMs, plan.settings.fps),
    ]));

    const anchorFrame = (anchor: TimingAnchor | undefined, fallback: "start" | "end", path: (string | number)[]): number => {
      if (!anchor) return fallback === "start" ? 0 : durationFrames;
      let base: number;
      if (anchor.type === "scene-start") base = 0;
      else if (anchor.type === "scene-end") base = durationFrames;
      else {
        const found = cueFrames.get(anchor.cue);
        if (found === undefined) {
          issues.push({ path: [...path, "cue"], message: `missing cue '${anchor.cue}' in scene '${item.id}'` });
          return 0;
        }
        base = found;
      }
      const frame = base + signedMillisecondsToFrames(anchor.offsetMs, plan.settings.fps);
      if (frame < 0 || frame > durationFrames) {
        issues.push({ path, message: `anchor resolves outside scene interval 0..${durationFrames}` });
      }
      return frame;
    };

    const layers = item.layers.map((layer, layerIndex) => {
      const start = anchorFrame(layer.from, "start", ["scenes", sceneIndex, "layers", layerIndex, "from"]);
      const end = anchorFrame(layer.to, "end", ["scenes", sceneIndex, "layers", layerIndex, "to"]);
      if (end < start) {
        issues.push({ path: ["scenes", sceneIndex, "layers", layerIndex], message: "layer end precedes its start" });
      }
      return { id: layer.id, type: layer.type, props: layer.props, startFrame: timelineFrame + start, endFrame: timelineFrame + end };
    });
    const tools = item.tools.map((tool, toolIndex) => {
      const start = anchorFrame(tool.at, "start", ["scenes", sceneIndex, "tools", toolIndex, "at"]);
      const end = anchorFrame(tool.until, "end", ["scenes", sceneIndex, "tools", toolIndex, "until"]);
      if (end < start) {
        issues.push({ path: ["scenes", sceneIndex, "tools", toolIndex], message: "tool end precedes its start" });
      }
      return {
        id: tool.id,
        tool: tool.tool,
        input: tool.input,
        frame: timelineFrame + start,
        startFrame: timelineFrame + start,
        endFrame: timelineFrame + end,
      };
    });
    const cues = Object.fromEntries([...cueFrames].map(([name, frame]) => [name, timelineFrame + frame]));
    const words = sceneAlignment.words.map((word) => ({
      token: word.token,
      startFrame: timelineFrame + millisecondsToFrame(word.startMs, plan.settings.fps),
      endFrame: timelineFrame + millisecondsToFrame(word.endMs, plan.settings.fps),
    }));
    const compiled: CompiledScene = {
      id: item.id,
      narration: { ...parsedNarration, words },
      durationMs: sceneAlignment.durationMs,
      startFrame: timelineFrame,
      endFrame: timelineFrame + durationFrames,
      cues,
      layers,
      tools,
    };
    timelineFrame += durationFrames;
    return compiled;
  });

  if (issues.length > 0) throw new CompileError(issues);
  return { fps: plan.settings.fps, durationFrames: timelineFrame, scenes };
}

function normalizeSpeech(value: string): string {
  return value.normalize("NFC").replace(/\s+/g, " ").trim();
}

function normalizeSpeechPrefix(value: string): string {
  return value.normalize("NFC").replace(/\s+/g, " ").trimStart();
}

function tokenize(value: string): string[] {
  const trimmed = value.trim();
  return trimmed === "" ? [] : trimmed.split(" ");
}

function signedMillisecondsToFrames(milliseconds: number, fps: number): number {
  return milliseconds < 0 ? -millisecondsToFrame(-milliseconds, fps) : millisecondsToFrame(milliseconds, fps);
}

function validateAlignment(
  narration: ParsedNarration,
  alignment: NarrationAlignment,
  alignmentIndex: number,
  issues: CompilerIssue[],
): void {
  if (alignment.words.length !== narration.tokens.length) {
    issues.push({
      path: ["alignments", alignmentIndex, "words"],
      message: `expected ${narration.tokens.length} word timings for narration, received ${alignment.words.length}`,
    });
  }
  alignment.words.forEach((word, wordIndex) => {
    if (wordIndex > 0 && word.startMs < alignment.words[wordIndex - 1]!.endMs) {
      issues.push({ path: ["alignments", alignmentIndex, "words", wordIndex, "startMs"], message: "word timings overlap or are out of order" });
    }
    if (word.endMs > alignment.durationMs) {
      issues.push({ path: ["alignments", alignmentIndex, "words", wordIndex, "endMs"], message: "word ends after narration duration" });
    }
  });
}

function parseAlignments(input: readonly unknown[]): NarrationAlignment[] {
  const output: NarrationAlignment[] = [];
  const issues: CompilerIssue[] = [];
  input.forEach((item, index) => {
    const parsed = narrationAlignmentSchema.safeParse(item);
    if (parsed.success) output.push(parsed.data);
    else issues.push(...parsed.error.issues.map((issue) => ({
      path: ["alignments", index, ...issue.path.map(pathPart)],
      message: issue.message,
    })));
  });
  if (issues.length > 0) throw new CompileError(issues);
  return output;
}

function zodCompileError(issues: z.ZodIssue[]): CompileError {
  return new CompileError(issues.map((issue) => ({ path: issue.path.map(pathPart), message: issue.message })));
}

function pathPart(part: PropertyKey): string | number {
  return typeof part === "symbol" ? part.toString() : part;
}

function formatPath(path: readonly (string | number)[]): string {
  if (path.length === 0) return "$";
  return path.reduce<string>((result, part) => typeof part === "number" ? `${result}[${part}]` : `${result}.${part}`, "$" );
}
