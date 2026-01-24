// ui/vitest.config.ts
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    // Run only unit tests inside src, file name ends with .test.ts/.test.tsx
    include: ["src/**/*.test.{ts,tsx}"],
    // Exclude Playwright e2e tests directory and *.spec.* naming
    exclude: [
      "tests/**",
      "**/*.spec.{ts,tsx}",
      "**/node_modules/**",
      "**/dist/**",
      "**/.{idea,git,cache,output,temp}/**"
    ],
    // Make describe/it/expect available as globals in tests (optional but safe)
    globals: true
  }
});
