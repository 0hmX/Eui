import type {CodeTokenizer, PreparedCodeLine} from "./types";

export interface ShikiTokenizerOptions {
  languages: readonly string[];
  themes?: readonly string[];
}

export async function createShikiTokenizer(options: ShikiTokenizerOptions): Promise<CodeTokenizer> {
  const themes = options.themes ?? ["github-dark"];
  // Loading Shiki is part of setup/preparation, never the render loop.
  // @ts-ignore The dependency may be absent in an offline source-only checkout.
  const {createHighlighter} = await import("shiki") as {createHighlighter(options: unknown): Promise<any>};
  const highlighter = await createHighlighter({
    langs: [...options.languages],
    themes: [...themes],
  });
  return {
    async tokenize(code, language, theme): Promise<readonly PreparedCodeLine[]> {
      if (!highlighter.getLoadedLanguages().includes(language)) {
        throw new Error(`Shiki language '${language}' was not loaded during preparation setup`);
      }
      if (!highlighter.getLoadedThemes().includes(theme)) {
        throw new Error(`Shiki theme '${theme}' was not loaded during preparation setup`);
      }
      return highlighter.codeToTokensBase(code, {lang: language, theme}).map((line: any[]) =>
        line.map((token: {content: string; color?: string; fontStyle?: number}) => ({
          content: token.content,
          color: token.color ?? "#ffffff",
          ...(token.fontStyle === undefined ? {} : {fontStyle: token.fontStyle}),
        })),
      );
    },
  };
}
