import { defineConfig } from "vite";
import { basename } from "node:path";

export default defineConfig({
  base: `/game0/demos/${basename(__dirname)}/`,
});
