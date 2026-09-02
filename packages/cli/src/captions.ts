import type { CompiledTimeline } from "@eui/compiler";

interface CaptionCue { startMs: number; endMs: number; text: string }

export function buildCaptionFiles(timeline: CompiledTimeline, maxWords = 7): { srt: string; vtt: string } {
  const cues: CaptionCue[] = [];
  for (const scene of timeline.scenes) {
    for (let index = 0; index < scene.narration.words.length; index += maxWords) {
      const words = scene.narration.words.slice(index, index + maxWords);
      if (words.length === 0) continue;
      cues.push({
        startMs: framesToMs(words[0]!.startFrame, timeline.fps),
        endMs: framesToMs(words.at(-1)!.endFrame, timeline.fps),
        text: words.map((word) => word.token).join(" "),
      });
    }
  }
  const srt = cues.map((cue, index) => `${index + 1}\n${stamp(cue.startMs, ",")} --> ${stamp(cue.endMs, ",")}\n${cue.text}\n`).join("\n");
  const vtt = `WEBVTT\n\n${cues.map((cue) => `${stamp(cue.startMs, ".")} --> ${stamp(cue.endMs, ".")}\n${cue.text}\n`).join("\n")}`;
  return { srt, vtt };
}

function framesToMs(frame: number, fps: number): number { return Math.round(frame * 1000 / fps); }
function stamp(milliseconds: number, separator: string): string {
  const hours = Math.floor(milliseconds / 3_600_000);
  const minutes = Math.floor(milliseconds / 60_000) % 60;
  const seconds = Math.floor(milliseconds / 1_000) % 60;
  const ms = milliseconds % 1_000;
  return `${pad(hours)}:${pad(minutes)}:${pad(seconds)}${separator}${ms.toString().padStart(3, "0")}`;
}
function pad(value: number): string { return value.toString().padStart(2, "0"); }
