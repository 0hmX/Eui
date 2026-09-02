import { resolveCueTimestamps } from "@eui/compiler";
import type { CueMarker, WordTiming } from "@eui/schema";

/**
 * Character offsets are authoritative; token offsets provide a boundary fallback for
 * punctuation-only narration. Mapping is monotonic, so repeated words resolve by occurrence rather
 * than by a text search. A cue inside a word uses that word's start. Punctuation is
 * attached to the preceding word; inter-word whitespace uses the next start, except
 * after sentence-ending punctuation where the preceding word's end is the boundary.
 * A cue at the complete narration end uses the clip duration.
 */
export function mapCuesToTimestamps(
  text: string,
  cues: readonly CueMarker[],
  words: readonly WordTiming[],
  durationMs: number,
): Record<string, number> {
  try {
    return resolveCueTimestamps(text, cues, words, durationMs);
  } catch (error) {
    throw new Error(`cannot map cues: ${error instanceof Error ? error.message : String(error)}`);
  }
}
