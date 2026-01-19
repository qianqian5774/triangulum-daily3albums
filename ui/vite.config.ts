import fs from "node:fs";
import path from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const repoRoot = path.resolve(__dirname, "..");
const buildDataDir = path.join(repoRoot, "_build", "public", "data");

function resolveBuildDataPath(urlPath: string): string | null {
  if (!urlPath.startsWith("/data/")) {
    return null;
  }
  const relative = urlPath.replace("/data/", "");
  const candidate = path.resolve(buildDataDir, relative);
  if (!candidate.startsWith(buildDataDir + path.sep)) {
    return null;
  }
  return candidate;
}

function contentTypeFor(filePath: string): string {
  if (filePath.endsWith(".json")) {
    return "application/json";
  }
  if (filePath.endsWith(".svg")) {
    return "image/svg+xml";
  }
  return "application/octet-stream";
}

export default defineConfig({
  base: "./",
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true
  },
  configureServer(server) {
    server.middlewares.use((req, res, next) => {
      const urlPath = (req.url || "").split("?")[0];
      if (!fs.existsSync(buildDataDir)) {
        next();
        return;
      }
      const filePath = resolveBuildDataPath(urlPath);
      if (!filePath || !fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
        next();
        return;
      }
      res.statusCode = 200;
      res.setHeader("Content-Type", contentTypeFor(filePath));
      fs.createReadStream(filePath).pipe(res);
    });
  }
});
