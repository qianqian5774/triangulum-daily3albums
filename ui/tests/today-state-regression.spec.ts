import { readFileSync } from "node:fs";
import path from "node:path";
import { expect, test } from "@playwright/test";

const repoRoot = path.resolve(import.meta.dirname, "..", "..");
const currentIssue = JSON.parse(
  readFileSync(path.join(repoRoot, "tests", "fixtures", "public_contract", "current-issue.json"), "utf8")
);
const archiveIndex = readFileSync(
  path.join(repoRoot, "tests", "fixtures", "public_contract", "current-index.json"),
  "utf8"
);
const staleIssue = { ...currentIssue, date: "2026-07-12", run_id: "stale-run" };
const imageBody = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl2nQAAAABJRU5ErkJggg==",
  "base64"
);

test("stale Today recovers through archive fallback and preserves overlay navigation", async ({ page }) => {
  let todayCalls = 0;
  await page.addInitScript(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
    window.localStorage.setItem("tri_ui_language", "en");
    window.localStorage.setItem("tri_ui_font_scale", "1");
  });
  await page.route("**/data/today.json*", (route) => {
    todayCalls += 1;
    const isExplicitRetry = new URL(route.request().url()).searchParams.has("t");
    const body = isExplicitRetry ? JSON.stringify(currentIssue) : JSON.stringify(staleIssue);
    return route.fulfill({ status: 200, contentType: "application/json", body });
  });
  await page.route("**/data/index.json*", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: archiveIndex })
  );
  await page.route("**/data/archive/**", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(currentIssue) })
  );
  await page.route("**/covers/**", (route) =>
    route.fulfill({ status: 200, contentType: "image/png", body: imageBody })
  );

  await page.goto(`/#/today?debug=1&debug_time=${currentIssue.date}T16:00:00`);
  await expect(page.getByText("ESTABLISHING LINK...", { exact: true }).first()).toBeVisible();
  await expect(page.getByTestId("album-card-0")).toBeVisible();
  const callsBeforeRetry = todayCalls;

  await page.getByRole("button", { name: "RETRY NOW" }).click();
  await expect(page.getByText("LINK RESTORED", { exact: true }).first()).toBeVisible();
  await expect(page.getByTestId("album-card-0")).toBeVisible();
  expect(todayCalls).toBe(callsBeforeRetry + 1);

  await page.getByTestId("album-card-0").click();
  await expect(page.getByTestId("treatment-overlay")).toBeVisible();
  const firstTitle = currentIssue.slots[2].picks[0].title;
  const secondTitle = currentIssue.slots[2].picks[1].title;
  await expect(page.getByTestId("treatment-overlay")).toHaveAttribute("aria-label", firstTitle);
  await page.keyboard.press("ArrowRight");
  await expect(page.getByTestId("treatment-overlay")).toHaveAttribute("aria-label", secondTitle);
  await page.keyboard.press("Escape");
  await expect(page.getByTestId("treatment-overlay")).toBeHidden();

  await page.getByTestId("share-card-toggle").click();
  await expect(page.getByRole("dialog", { name: "Share Card" })).toBeVisible();
  await page.getByRole("button", { name: "Close", exact: true }).click();
  await expect(page.getByRole("dialog", { name: "Share Card" })).toBeHidden();

  await page.waitForTimeout(1100);
  expect(todayCalls).toBe(callsBeforeRetry + 1);
});

test("failed Today uses current last-good data before archive fallback", async ({ page }) => {
  let archiveIndexCalls = 0;
  await page.addInitScript((payload) => {
    window.localStorage.clear();
    window.sessionStorage.clear();
    window.localStorage.setItem("tri_ui_language", "en");
    window.localStorage.setItem("lastGoodTodayJson", JSON.stringify(payload));
    window.localStorage.setItem("lastGoodDateKey", payload.date);
  }, currentIssue);
  await page.route("**/data/today.json*", (route) =>
    route.fulfill({ status: 503, contentType: "text/plain", body: "unavailable" })
  );
  await page.route("**/data/index.json*", (route) => {
    archiveIndexCalls += 1;
    return route.fulfill({ status: 500, contentType: "text/plain", body: "should not be requested" });
  });
  await page.route("**/covers/**", (route) =>
    route.fulfill({ status: 200, contentType: "image/png", body: imageBody })
  );

  await page.goto(`/#/today?debug=1&debug_time=${currentIssue.date}T16:00:00`);
  await expect(page.getByText("ESTABLISHING LINK...", { exact: true }).first()).toBeVisible();
  await expect(page.getByTestId("album-card-0")).toBeVisible();
  await expect(page.getByText(currentIssue.slots[2].picks[0].title, { exact: true })).toBeVisible();
  expect(archiveIndexCalls).toBe(0);
});

test("Offline State restores the locked archive surface", async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
    window.localStorage.setItem("tri_ui_language", "en");
  });
  await page.route("**/data/today.json*", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(currentIssue) })
  );
  await page.route("**/data/index.json*", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: archiveIndex })
  );
  await page.route("**/data/archive/**", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(currentIssue) })
  );
  await page.route("**/covers/**", (route) =>
    route.fulfill({ status: 200, contentType: "image/png", body: imageBody })
  );

  await page.goto(`/#/today?debug=1&debug_time=${currentIssue.date}T07:59:59`);
  await expect(page.getByRole("heading", { name: "SYSTEM OFFLINE" })).toBeVisible();
  await expect(page.getByText("Yesterday's intake (archived)", { exact: true })).toBeVisible();
  await expect(page.getByText("Album 4", { exact: true })).toBeVisible();
});
