declare module "node:fs/promises" {
  export function access(path: string): Promise<void>;
  export function copyFile(source: string, destination: string): Promise<void>;
  export function mkdir(path: string, options?: { recursive?: boolean }): Promise<string | undefined>;
  export function mkdtemp(prefix: string): Promise<string>;
  export function readFile(path: string): Promise<Uint8Array>;
  export function readFile(path: string, encoding: "utf8"): Promise<string>;
  export function rename(oldPath: string, newPath: string): Promise<void>;
  export function rm(path: string, options?: { recursive?: boolean; force?: boolean }): Promise<void>;
  export function stat(path: string): Promise<{ isFile(): boolean; isDirectory(): boolean; size: number }>;
  export function writeFile(path: string, data: string | Uint8Array, options?: { flag?: string }): Promise<void>;
}
declare module "node:path" {
  export function basename(path: string): string;
  export function dirname(path: string): string;
  export function join(...parts: string[]): string;
  export function relative(from: string, to: string): string;
  export function resolve(...parts: string[]): string;
}
declare module "node:url" {
  export function fileURLToPath(url: string): string;
  export function pathToFileURL(path: string): { href: string };
}
declare const Bun: {
  argv: string[];
  file(path: string): { delete(): Promise<void> };
  write(path: string, data: string | Uint8Array): Promise<number>;
  spawn(command: string[], options?: { stdin?: "pipe" | "ignore"; stdout?: "pipe" | "ignore"; stderr?: "pipe" | "ignore"; cwd?: string; env?: Record<string, string | undefined> }): {
    stdin: { write(data: string): void; end(): void };
    stdout: ReadableStream<Uint8Array>;
    stderr: ReadableStream<Uint8Array>;
    exited: Promise<number>;
  };
  spawn(options: { cmd: string[]; stdin?: "pipe" | "ignore"; stdout?: "pipe"; stderr?: "pipe" | "ignore"; cwd?: string; env?: Record<string, string | undefined> }): {
    stdin: { write(data: string): void; end(): void };
    stdout: ReadableStream<Uint8Array>;
    stderr: ReadableStream<Uint8Array>;
    exited: Promise<number>;
  };
};
declare const process: { cwd(): string; env: Record<string, string | undefined>; exitCode?: number };
interface ImportMeta { main: boolean }
