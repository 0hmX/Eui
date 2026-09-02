declare module "node:fs/promises" {
  export function mkdir(path: string, options?: { recursive?: boolean }): Promise<string | undefined>;
  export function readFile(path: string): Promise<Uint8Array>;
  export function writeFile(path: string, data: string | Uint8Array, options?: { flag?: string }): Promise<void>;
  export function rename(oldPath: string, newPath: string): Promise<void>;
  export function rm(path: string, options?: { recursive?: boolean; force?: boolean }): Promise<void>;
  export function stat(path: string): Promise<{ isFile(): boolean; size: number }>;
}

declare module "node:path" {
  export function join(...parts: string[]): string;
  export function resolve(...parts: string[]): string;
  export function dirname(path: string): string;
}

declare const Bun: {
  spawn(options: {
    cmd: string[];
    cwd?: string;
    stdin: "pipe";
    stdout: "pipe";
    stderr: "pipe";
    env?: Record<string, string | undefined>;
  }): {
    stdin: { write(data: string): void; end(): void };
    stdout: ReadableStream<Uint8Array>;
    stderr: ReadableStream<Uint8Array>;
    exited: Promise<number>;
  };
};

declare const process: {
  cwd(): string;
  env: Record<string, string | undefined>;
};
