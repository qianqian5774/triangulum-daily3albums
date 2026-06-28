import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import type { PlaywrightTestConfig } from "@playwright/test";

type BrowserChannel = NonNullable<NonNullable<PlaywrightTestConfig["use"]>["channel"]>;

const uiDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(uiDir, "..");
const localPython = process.platform === "win32"
  ? path.join(repoRoot, ".venv", "Scripts", "python.exe")
  : path.join(repoRoot, ".venv", "bin", "python");
const pythonCommand = existsSync(localPython) ? `"${localPython}"` : "python3";
const publicDir = process.env.PLAYWRIGHT_WEB_ROOT ?? path.join(repoRoot, "_build", "public");
const chromiumChannel = process.env.PLAYWRIGHT_CHROMIUM_CHANNEL as BrowserChannel | undefined;
const chromiumExecutablePath = process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH;

const config: PlaywrightTestConfig = {
  testDir: "./tests",
  outputDir: "./artifacts/playwright",
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:8000",
    screenshot: "only-on-failure",
    channel: chromiumChannel,
    launchOptions: chromiumExecutablePath ? { executablePath: chromiumExecutablePath } : undefined
  },
  webServer: {
    url: "http://127.0.0.1:8000",
    command: `${pythonCommand} -m http.server 8000`,
    cwd: publicDir,
    reuseExistingServer: true
  }
};

export default config;
