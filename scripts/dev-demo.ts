// Usage: bun run dev:demo <name>
import { $ } from "bun";
const name = process.argv[2];
if (!name) throw new Error("Usage: bun run dev:demo <name>");
await $`bun run dev`.cwd(`demos/${name}`);
