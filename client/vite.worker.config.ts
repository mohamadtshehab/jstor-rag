import { resolve } from "path";
import { defineConfig } from "vite";

export default defineConfig({
  build: {
    outDir: "dist",
    emptyOutDir: false,
    lib: {
      entry: resolve(__dirname, "src/background/service-worker.ts"),
      formats: ["es"],
      fileName: () => "service-worker.js",
    },
    rollupOptions: {
      output: {
        entryFileNames: "service-worker.js",
      },
    },
  },
});
