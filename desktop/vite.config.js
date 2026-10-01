import { defineConfig } from "vite";
import { sveltekit } from "@sveltejs/kit/vite";
import process from "node:process";
import path from "node:path";
import { fileURLToPath } from "node:url";
// @ts-expect-error serve-static ships no types and checkJs is enabled
import serveStatic from "serve-static";

const host = process.env.TAURI_DEV_HOST;
const cesiumRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "node_modules/cesium/Build/Cesium");

export default defineConfig(() => ({
  plugins: [
    sveltekit(),
    {
      name: "cesium-static",
      configureServer(server) {
        server.middlewares.use("/cesium", serveStatic(cesiumRoot));
      },
    },
  ],
  // Vite options tailored for Tauri development and only applied in `tauri dev` or `tauri build`
  //
  // 1. prevent Vite from obscuring rust errors
  clearScreen: false,
  // 2. tauri expects a fixed port, fail if that port is not available
  server: {
    port: 1420,
    strictPort: true,
    host: host || "127.0.0.1",
    hmr: host
      ? {
          protocol: "ws",
          host,
          port: 1421,
        }
      : undefined,
    watch: {
      // 3. tell Vite to ignore watching `src-tauri`
      ignored: ["**/src-tauri/**"],
    },
  },
}));
