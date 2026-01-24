import { mkdir } from "node:fs/promises";
import path from "node:path";
import { test, type Page } from "@playwright/test";

const outputDir = path.join("artifacts", "screenshots", "phase2");

async function ensureOutputDir() {
  await mkdir(outputDir, { recursive: true });
}

async function visitToday(page: Page, view: string) {
  await page.goto(`/#/?view=${view}`);
  await page.waitForSelector('[data-testid="album-card-0"]', { state: "visible" });
}

test("capture phase II screenshots", async ({ page }) => {
  await ensureOutputDir();

  await page.setViewportSize({ width: 1440, height: 900 });
  await visitToday(page, "desktop");
  await page.screenshot({ path: path.join(outputDir, "today-desktop.png"), fullPage: true });
  await page.click('[data-testid="ambient-toggle"]');
  await page.waitForSelector("section.ambient-mode");
  await page.screenshot({ path: path.join(outputDir, "today-ambient.png"), fullPage: true });

  await page.setViewportSize({ width: 390, height: 844 });
  await visitToday(page, "mobile");
  await page.screenshot({ path: path.join(outputDir, "today-mobile.png"), fullPage: true });

  await page.setViewportSize({ width: 1440, height: 900 });
  await visitToday(page, "overlay-desktop");
  await page.click('[data-testid="album-card-0"]');
  await page.waitForSelector('[data-testid="treatment-overlay"]', { state: "visible" });
  await page.screenshot({ path: path.join(outputDir, "overlay-desktop.png"), fullPage: false });
  await page.keyboard.press("Escape");
  await page.waitForSelector('[data-testid="treatment-overlay"]', { state: "hidden" });

  await page.setViewportSize({ width: 390, height: 844 });
  await visitToday(page, "overlay-mobile");
  await page.click('[data-testid="album-card-0"]');
  await page.waitForSelector('[data-testid="treatment-overlay"]', { state: "visible" });
  await page.screenshot({ path: path.join(outputDir, "overlay-mobile.png"), fullPage: false });
});
