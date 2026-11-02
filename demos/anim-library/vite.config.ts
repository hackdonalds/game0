import { defineConfig } from "vite";
import { basename, resolve } from "node:path";

// Serves the animation library straight from art/anims, so the clips aren't copied into the repo twice
export default defineConfig({
  base: `/game0/demos/${basename(__dirname)}/`,
  publicDir: resolve(__dirname, "../../art/anims"),
});
