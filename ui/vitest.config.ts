import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    // 只跑单元测试：你放在 src 里，文件名以 .test.ts/.test.tsx 结尾
    include: ["src/**/*.test.{ts,tsx}"],
    // 明确排除 Playwright 的 tests 目录，以及 e2e spec 命名
    exclude: [
      "tests/**",
      "**/*.spec.{ts,tsx}",
      "**/node_modules/**",
      "**/dist/**",
      "**/.{idea,git,cache,output,temp}/**"
    ]
  }
});
