import type { PlaywrightTestConfig } from "@playwright/test";

const config: PlaywrightTestConfig = {
  testDir: "./tests",
  outputDir: "./artifacts/playwright",
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:8000",
    screenshot: "only-on-failure"
  },
  webServer: {
    url: "http://127.0.0.1:8000",
    command: "python3 -m http.server 8000",
    cwd: "../_build/public",
    reuseExistingServer: true
  }
};

export default config;
