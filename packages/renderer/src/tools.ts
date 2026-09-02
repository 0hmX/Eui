import {z} from "zod";
import {ToolRegistry} from "./registry";
import type {VisualTool} from "./types";

const positionSchema = z.tuple([z.number().finite(), z.number().finite()]).default([0, 0]);
const lineNumbersSchema = z.array(z.number().int().positive()).default([]);
const codeStyleSchema = {
  language: z.string().min(1).default("typescript"),
  theme: z.string().min(1).default("github-dark"),
  focus: lineNumbersSchema,
  selection: lineNumbersSchema,
  position: positionSchema,
  fontSize: z.number().positive().default(36),
};

const textInputSchema = z.object({
  text: z.string(),
  position: positionSchema,
  color: z.string().min(1).default("#ffffff"),
  fontSize: z.number().positive().default(64),
  align: z.enum(["left", "center", "right"]).default("center"),
}).strict();

const imageInputSchema = z.object({
  source: z.string().min(1),
  alt: z.string().default(""),
  position: positionSchema,
  size: z.tuple([z.number().positive(), z.number().positive()]).optional(),
  fit: z.enum(["contain", "cover", "fill"]).default("contain"),
}).strict();

const captionsInputSchema = z.object({
  mode: z.enum(["word", "phrase"]).default("phrase"),
  maxWords: z.number().int().positive().max(20).default(7),
  position: positionSchema,
  color: z.string().min(1).default("#ffffff"),
  activeColor: z.string().min(1).default("#ffd166"),
  fontSize: z.number().positive().default(52),
}).strict();

const codeInputSchema = z.object({
  source: z.string(),
  ...codeStyleSchema,
}).strict();

export type TextInput = z.infer<typeof textInputSchema>;
export type ImageInput = z.infer<typeof imageInputSchema>;
export type CaptionsInput = z.infer<typeof captionsInputSchema>;
export type CodeInput = z.infer<typeof codeInputSchema>;

export const textTool: VisualTool<TextInput> = {
  name: "text",
  inputSchema: textInputSchema,
  prepare(input) {
    return {kind: "text", data: input};
  },
};

function imageTool(name: string): VisualTool<ImageInput> {
  return {
    name,
    inputSchema: imageInputSchema,
    async prepare(input, context) {
      const asset = await context.assetLoader.load(input.source);
      return {kind: "media.image", data: {...input, asset}};
    },
  };
}

export const mediaImageTool = imageTool("media.image");
export const imageToolAlias = imageTool("image");

export const captionsTool: VisualTool<CaptionsInput> = {
  name: "captions",
  inputSchema: captionsInputSchema,
  prepare(input, context) {
    const words = context.scene.narration.words.filter(
      (word) => word.endFrame > context.invocation.startFrame && word.startFrame < context.invocation.endFrame,
    );
    const groups = input.mode === "word"
      ? words.map((word) => [word])
      : Array.from({length: Math.ceil(words.length / input.maxWords)}, (_, index) =>
          words.slice(index * input.maxWords, (index + 1) * input.maxWords),
        );
    return {
      kind: "captions",
      data: {
        ...input,
        groups: groups.map((group) => ({
          text: group.map((word) => word.token).join(" "),
          startFrame: group[0]?.startFrame ?? context.invocation.startFrame,
          endFrame: group.at(-1)?.endFrame ?? context.invocation.endFrame,
          words: group,
        })),
      },
    };
  },
};

export const codeTool: VisualTool<CodeInput> = {
  name: "code",
  inputSchema: codeInputSchema,
  async prepare(input, context) {
    const tokens = await context.tokenizer.tokenize(input.source, input.language, input.theme);
    const sourceLines = splitLines(input.source);
    return {
      kind: "code",
      data: {
        ...input,
        lines: sourceLines.map((text, index) => ({
          id: `line-${index + 1}`,
          lineNumber: index + 1,
          text,
          tokens: tokens[index] ?? [],
          focused: input.focus.includes(index + 1),
          selected: input.selection.includes(index + 1),
        })),
      },
    };
  },
};

export function createDefaultToolRegistry(): ToolRegistry {
  return new ToolRegistry([textTool, mediaImageTool, imageToolAlias, captionsTool, codeTool]);
}

function splitLines(value: string): string[] {
  return value.replace(/\r\n/g, "\n").split("\n");
}
