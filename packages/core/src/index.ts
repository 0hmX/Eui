import type { Scene, VideoPlan } from "@eui/schema";

type AuthoredScene = Omit<Scene, "layers" | "tools"> &
  Partial<Pick<Scene, "layers" | "tools">>;

type AuthoredVideo = Omit<VideoPlan, "scenes"> & { scenes: readonly AuthoredScene[] };

/** Marks a location in narration without adding spoken text. */
export function cue<const Name extends string>(name: Name): `[[cue:${Name}]]` {
  return `[[cue:${name}]]`;
}

/** Applies scene defaults while retaining literal ids and layer types. */
export function scene<const Definition extends AuthoredScene>(definition: Definition): Definition & Scene {
  return {
    layers: [],
    tools: [],
    ...definition,
  } as Definition & Scene;
}

/** Declares a JSON-compatible video plan. Validation happens at the compiler boundary. */
export function defineVideo<const Definition extends AuthoredVideo>(definition: Definition): Definition & VideoPlan {
  return definition as Definition & VideoPlan;
}

export type { Scene, VideoPlan } from "@eui/schema";
