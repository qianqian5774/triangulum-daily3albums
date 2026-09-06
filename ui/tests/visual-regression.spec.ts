import { readFileSync } from "node:fs";
import { mkdir } from "node:fs/promises";
import path from "node:path";
import { expect, test, type Page } from "@playwright/test";

const repoRoot = path.resolve(import.meta.dirname, "..", "..");
const issueBytes = readFileSync(path.join(repoRoot, "tests", "fixtures", "public_contract", "current-issue.json"));
const indexBytes = readFileSync(path.join(repoRoot, "tests", "fixtures", "public_contract", "current-index.json"));
const issue = JSON.parse(issueBytes.toString("utf8"));
const outputDir = process.env.VISUAL_OUTPUT_DIR;
const imageBody = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl2nQAAAABJRU5ErkJggg==",
  "base64"
);

async function setupDeterministicData(page: Page) {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.addInitScript(() => {
    window.localStorage.setItem("tri_ui_language", "en");
    window.localStorage.setItem("tri_ui_font_scale", "1");
  });
  await page.route("**/data/today.json*", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: issueBytes })
  );
  await page.route("**/data/index.json*", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: indexBytes })
  );
  await page.route("**/data/archive/2026-07-13/**", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: issueBytes })
  );
  await page.route("**/data/archive/2026-07-13.json*", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: issueBytes })
  );
  await page.route("**/covers/**", (route) =>
    route.fulfill({ status: 200, contentType: "image/png", body: imageBody })
  );
}

const settleVisualState = (page: Page) => page.waitForTimeout(1600);

async function capture(page: Page, fileName: string, fullPage = true) {
  if (!outputDir) {
    throw new Error("VISUAL_OUTPUT_DIR is required");
  }
  await mkdir(outputDir, { recursive: true });
  await page.screenshot({
    path: path.join(outputDir, fileName),
    fullPage,
    animations: "disabled"
  });
}

test("capture deterministic R5 visual surfaces", async ({ page }) => {
  await setupDeterministicData(page);
  await page.setViewportSize({ width: 1280, height: 720 });

  await page.goto(`/#/today?debug=1&debug_time=${issue.date}T07:59:59`);
  await expect(page.getByRole("heading", { name: "SYSTEM OFFLINE" })).toBeVisible();
  await expect(page.getByText("Album 4", { exact: true })).toBeVisible();
  await settleVisualState(page);
  await capture(page, "offline.png");

  await page.goto(`/#/today?debug=1&debug_time=${issue.date}T16:00:00`);
  await expect(page.getByTestId("album-card-0")).toBeVisible();
  await settleVisualState(page);
  await capture(page, "today.png");

  await page.getByTestId("share-card-toggle").click();
  await expect(page.getByRole("dialog", { name: "Share Card" })).toBeVisible();
  await settleVisualState(page);
  await capture(page, "share-card.png", false);
  await page.getByRole("button", { name: "Close", exact: true }).click();

  await page.getByTestId("album-card-0").click();
  await expect(page.getByTestId("treatment-overlay")).toBeVisible();
  await expect(page.getByTestId("viewer-cover-frame")).toHaveAttribute("data-cover-status", "ready");
  await settleVisualState(page);
  await capture(page, "viewer.png", false);

  await page.goto(`/#/archive?debug=1&debug_time=${issue.date}T16:00:00`);
  await expect(page.getByRole("heading", { name: "Recent archive" })).toBeVisible();
  await expect(page.locator("article")).toHaveCount(1);
  await settleVisualState(page);
  await capture(page, "archive.png");
});
