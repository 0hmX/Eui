import { mkdir, readFile, rename, rm, stat, writeFile } from "node:fs/promises";
import { join } from "node:path";
import { alignmentCacheManifestSchema, audioCacheManifestSchema, type AlignmentCacheManifest, type AudioCacheManifest } from "./manifest";
import { sha256, stableJson } from "./hash";
import type { AudioArtifact, SynthesisResult } from "./types";

export interface CachedAudio { manifest: AudioCacheManifest; artifact: AudioArtifact; bytes: Uint8Array }

async function parseJsonFile(path: string): Promise<unknown> {
  return JSON.parse(new TextDecoder().decode(await readFile(path)));
}

export async function lookupAudio(cacheRoot: string, key: string): Promise<CachedAudio | undefined> {
  const directory = join(cacheRoot, "audio", key);
  try {
    const manifest = audioCacheManifestSchema.parse(await parseJsonFile(join(directory, "manifest.json")));
    if (manifest.synthesisKey !== key) return undefined;
    const path = join(directory, manifest.artifact.file);
    const bytes = await readFile(path);
    if (bytes.byteLength !== manifest.artifact.bytes || await sha256(bytes) !== manifest.artifact.sha256) return undefined;
    const artifact: AudioArtifact = {
      path,
      sha256: manifest.artifact.sha256,
      bytes: manifest.artifact.bytes,
      mediaType: manifest.artifact.mediaType,
      ...(manifest.artifact.sampleRate === undefined ? {} : { sampleRate: manifest.artifact.sampleRate }),
    };
    return { manifest, artifact, bytes };
  } catch {
    return undefined;
  }
}

export async function writeAudioAtomically(
  cacheRoot: string,
  manifestBase: Omit<AudioCacheManifest, "artifact">,
  result: SynthesisResult,
): Promise<CachedAudio> {
  if (!/^[A-Za-z0-9]+$/.test(result.extension)) throw new Error(`invalid audio extension '${result.extension}'`);
  if (result.audio.byteLength === 0) throw new Error("audio provider returned an empty artifact");
  const parent = join(cacheRoot, "audio");
  await mkdir(parent, { recursive: true });
  const destination = join(parent, manifestBase.synthesisKey);
  const temporary = join(parent, `.${manifestBase.synthesisKey}.${crypto.randomUUID()}.tmp`);
  await mkdir(temporary);
  try {
    const file = `audio.${result.extension}`;
    const digest = await sha256(result.audio);
    const artifact = {
      file,
      sha256: digest,
      bytes: result.audio.byteLength,
      mediaType: result.mediaType,
      ...(result.sampleRate === undefined ? {} : { sampleRate: result.sampleRate }),
    };
    const manifest = audioCacheManifestSchema.parse({ ...manifestBase, artifact });
    await writeFile(join(temporary, file), result.audio, { flag: "wx" });
    // The manifest is the validity marker and is always written after the artifact.
    await writeFile(join(temporary, "manifest.json"), `${stableJson(manifest)}\n`, { flag: "wx" });
    const raced = await installCacheDirectory(temporary, destination, () => lookupAudio(cacheRoot, manifestBase.synthesisKey));
    if (raced) return raced;
    const cached = await lookupAudio(cacheRoot, manifestBase.synthesisKey);
    if (!cached) throw new Error("audio cache verification failed after write");
    return cached;
  } finally {
    await rm(temporary, { recursive: true, force: true });
  }
}

export async function lookupAlignment(cacheRoot: string, key: string): Promise<AlignmentCacheManifest | undefined> {
  try {
    const value = alignmentCacheManifestSchema.parse(await parseJsonFile(join(cacheRoot, "alignments", key, "manifest.json")));
    return value.alignmentKey === key ? value : undefined;
  } catch {
    return undefined;
  }
}

export async function writeAlignmentAtomically(cacheRoot: string, manifestInput: AlignmentCacheManifest): Promise<AlignmentCacheManifest> {
  const manifest = alignmentCacheManifestSchema.parse(manifestInput);
  const parent = join(cacheRoot, "alignments");
  await mkdir(parent, { recursive: true });
  const destination = join(parent, manifest.alignmentKey);
  const temporary = join(parent, `.${manifest.alignmentKey}.${crypto.randomUUID()}.tmp`);
  await mkdir(temporary);
  try {
    await writeFile(join(temporary, "manifest.json"), `${stableJson(manifest)}\n`, { flag: "wx" });
    const raced = await installCacheDirectory(temporary, destination, () => lookupAlignment(cacheRoot, manifest.alignmentKey));
    if (raced) return raced;
    const cached = await lookupAlignment(cacheRoot, manifest.alignmentKey);
    if (!cached) throw new Error("alignment cache verification failed after write");
    return cached;
  } finally {
    await rm(temporary, { recursive: true, force: true });
  }
}

/**
 * Directory rename makes the manifest and payload visible together. If a previous writer left a
 * corrupt destination, move it aside atomically before retrying; a valid concurrent winner always
 * takes precedence over the local temporary directory.
 */
async function installCacheDirectory<T>(
  temporary: string,
  destination: string,
  lookup: () => Promise<T | undefined>,
): Promise<T | undefined> {
  try {
    await rename(temporary, destination);
    return undefined;
  } catch (initialError) {
    const winner = await lookup();
    if (winner) return winner;
    const displaced = `${destination}.${crypto.randomUUID()}.invalid`;
    let movedInvalidDestination = false;
    try {
      try {
        await rename(destination, displaced);
        movedInvalidDestination = true;
      } catch {
        const concurrentWinner = await lookup();
        if (concurrentWinner) return concurrentWinner;
      }
      try {
        await rename(temporary, destination);
        return undefined;
      } catch (retryError) {
        const concurrentWinner = await lookup();
        if (concurrentWinner) return concurrentWinner;
        throw retryError ?? initialError;
      }
    } finally {
      if (movedInvalidDestination) await rm(displaced, { recursive: true, force: true });
    }
  }
}

export async function hashFile(path: string): Promise<string> {
  const info = await stat(path);
  if (!info.isFile()) throw new Error(`voice reference is not a file: ${path}`);
  return sha256(await readFile(path));
}
