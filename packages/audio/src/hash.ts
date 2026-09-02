import type { StableValue } from "./types";

export function normalizeNarration(value: string): string {
  return value.normalize("NFC").replace(/\s+/gu, " ").trim();
}

export function stableJson(value: StableValue): string {
  if (value === undefined) return "null";
  if (value === null || typeof value === "boolean" || typeof value === "string") return JSON.stringify(value);
  if (typeof value === "number") {
    if (!Number.isFinite(value)) throw new TypeError("stable JSON only supports finite numbers");
    return JSON.stringify(value);
  }
  if (Array.isArray(value)) return `[${value.map(stableJson).join(",")}]`;
  const entries = Object.entries(value)
    .filter((entry) => entry[1] !== undefined)
    .sort(([left], [right]) => left < right ? -1 : left > right ? 1 : 0);
  return `{${entries.map(([key, item]) => `${JSON.stringify(key)}:${stableJson(item)}`).join(",")}}`;
}

export async function sha256(data: string | Uint8Array): Promise<string> {
  const bytes = typeof data === "string" ? new TextEncoder().encode(data) : data;
  const copy = new Uint8Array(bytes.byteLength);
  copy.set(bytes);
  const digest = await crypto.subtle.digest("SHA-256", copy.buffer);
  return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

export async function hashNarration(value: string): Promise<string> {
  return sha256(normalizeNarration(value));
}

export async function stableCacheKey(namespace: string, value: StableValue): Promise<string> {
  return sha256(`${namespace}\0${stableJson(value)}`);
}
