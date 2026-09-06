import { expect, test, type Page, type Route } from "@playwright/test";

const AUDIT_DATE = "2026-07-12";
const COVER_PATTERN = "https://coverartarchive.org/**";
const FIRST_VISIBLE_ALBUM = 7;
const FIRST_VISIBLE_COVER = "cover-6";
const SECOND_VISIBLE_COVER = "cover-7";
const IMAGE_BODY = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wl2nQAAAABJRU5ErkJggg==",
  "base64"
);

function makePick(index: number) {
  const slot = (["Headliner", "Lineage", "DeepCut"] as const)[index % 3];
  return {
    slot,
    rg_mbid: `00000000-0000-4000-8000-${String(index + 1).padStart(12, "0")}`,
    title: `Album ${index + 1}`,
    artist_credit: `Artist ${index + 1}`,
    first_release_year: 2000 + index,
    tags: [{ name: `tag-${index + 1}` }],
    musicbrainz: {
      rating: { value: 4.1, votes_count: 12 },
      tags: [{ name: "signal" }],
      overview: {
        text: `Overview for album ${index + 1}`,
        source_url: "https://example.com/source",
        license_url: "https://creativecommons.org/licenses/by-sa/3.0/"
      }
    },
    cover: {
      has_cover: true,
      optimized_cover_url: `https://coverartarchive.org/test/cover-${index}.png`,
      cover_version: "viewer-regression"
    },
    links: {
      musicbrainz: `https://musicbrainz.org/release-group/rg-${index}`,
      youtube_search: `https://www.youtube.com/results?search_query=album+${index + 1}`
    }
  };
}

const picks = Array.from({ length: 9 }, (_, index) => makePick(index));
const issue = {
  output_schema_version: "1.0",
  date: AUDIT_DATE,
  run_id: "viewer-cover-regression",
  theme_of_day: "viewer regression",
  now_slot_id: 2,
  picks: picks.slice(6, 9),
  slots: [0, 1, 2].map((slotId) => ({
    slot_id: slotId,
    window_label: ["08:00-12:29", "12:30-15:59", "16:00-23:59"][slotId],
    theme: `theme-${slotId}`,
    picks: picks.slice(slotId * 3, slotId * 3 + 3)
  }))
};

type BrowserSignals = {
  consoleErrors: string[];
  pageErrors: string[];
  failedCoverRequests: string[];
  failedCoverResponses: number[];
};

async function setupPage(page: Page): Promise<BrowserSignals> {
  const signals: BrowserSignals = {
    consoleErrors: [],
    pageErrors: [],
    failedCoverRequests: [],
    failedCoverResponses: []
  };
  page.on("console", (message) => {
    if (message.type() === "error") signals.consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => signals.pageErrors.push(error.message));
  page.on("requestfailed", (request) => {
    if (request.url().startsWith("https://coverartarchive.org/")) {
      signals.failedCoverRequests.push(request.url());
    }
  });
  page.on("response", (response) => {
    if (response.url().startsWith("https://coverartarchive.org/") && response.status() >= 400) {
      signals.failedCoverResponses.push(response.status());
    }
  });
  await page.addInitScript(() => {
    const state = { cls: 0 };
    Object.defineProperty(window, "__viewerCoverAudit", { value: state, configurable: true });
    try {
      new PerformanceObserver((list) => {
        for (const entry of list.getEntries() as Array<PerformanceEntry & { hadRecentInput?: boolean; value?: number }>) {
          if (!entry.hadRecentInput) state.cls += entry.value ?? 0;
        }
      }).observe({ type: "layout-shift", buffered: true });
    } catch {
      // LayoutShift is not exposed in every browser mode; geometry assertions still run.
    }
  });
  await page.route("**/data/today.json*", (route) => route.fulfill({ json: issue }));
  await page.goto(`/#/today?debug=1&debug_time=${AUDIT_DATE}T16:00:00`);
  await page.getByTestId("album-card-0").waitFor({ state: "visible" });
  return signals;
}

async function openViewer(page: Page, index = 0) {
  await page.evaluate(() => {
    const state = (window as Window & { __viewerCoverAudit?: { cls: number } }).__viewerCoverAudit;
    if (state) state.cls = 0;
  });
  const started = performance.now();
  await page.getByTestId(`album-card-${index}`).click();
  const overlay = page.getByTestId("treatment-overlay");
  await overlay.waitFor({ state: "visible", timeout: 2500 });
  return { overlay, visibleAfterMs: performance.now() - started };
}

async function expectStableLayout(page: Page, before: { width: number; height: number } | null) {
  const after = await page.getByTestId("viewer-cover-frame").boundingBox();
  expect(before).not.toBeNull();
  expect(after).not.toBeNull();
  expect(Math.abs(after!.width - before!.width)).toBeLessThanOrEqual(1);
  expect(Math.abs(after!.height - before!.height)).toBeLessThanOrEqual(1);
  const layout = await page.evaluate(() => ({
    overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    cls: (window as Window & { __viewerCoverAudit?: { cls: number } }).__viewerCoverAudit?.cls ?? 0
  }));
  expect(layout.overflow).toBeLessThanOrEqual(1);
  expect(layout.cls).toBeLessThanOrEqual(0.02);
}

function expectNoRuntimeErrors(signals: BrowserSignals) {
  const unexpectedConsoleErrors = signals.consoleErrors.filter(
    (message) => !message.startsWith("Failed to load resource:")
  );
  expect(unexpectedConsoleErrors).toEqual([]);
  expect(signals.pageErrors).toEqual([]);
}

async function fulfillImage(route: Route) {
  await route.fulfill({
    status: 200,
    contentType: "image/png",
    body: IMAGE_BODY
  });
}

test("blocked Cover Art Archive does not block Viewer content or Escape", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.route(COVER_PATTERN, (route) => route.abort("blockedbyclient"));
  const signals = await setupPage(page);

  const { overlay, visibleAfterMs } = await openViewer(page);
  expect(visibleAfterMs).toBeLessThan(2500);
  await expect(overlay).toContainText(`Artist ${FIRST_VISIBLE_ALBUM}`);
  await expect(overlay).toContainText("4.1/5");
  await expect(overlay).toContainText(`Overview for album ${FIRST_VISIBLE_ALBUM}`);
  await expect(page.getByTestId("viewer-cover-placeholder")).toBeVisible();
  await expect(page.getByTestId("viewer-cover-frame")).toHaveAttribute("data-cover-status", "failed");
  expect(signals.failedCoverRequests.length).toBeGreaterThan(0);
  await page.keyboard.press("Escape");
  await expect(overlay).toBeHidden();
  expectNoRuntimeErrors(signals);
});

test("deployment-local cover manifest prevents Cover Art Archive requests", async ({ page }) => {
  const localCoverPath = "assets/covers/manifest-cover.png";
  const manifest = Object.fromEntries(
    Array.from({ length: 9 }, (_, index) => [
      `https://coverartarchive.org/test/cover-${index}.png`,
      localCoverPath
    ])
  );
  let localCoverRequests = 0;

  await page.route("**/assets/cover-manifest.js", (route) => route.fulfill({
    contentType: "application/javascript",
    body: `window.__TRIANGULUM_STATIC_COVERS__ = Object.freeze(${JSON.stringify(manifest)});`
  }));
  await page.route("**/assets/covers/manifest-cover.png*", async (route) => {
    localCoverRequests += 1;
    await fulfillImage(route);
  });
  await page.route(COVER_PATTERN, (route) => route.abort("blockedbyclient"));
  const signals = await setupPage(page);

  await openViewer(page);

  await expect(page.getByTestId("viewer-cover-frame")).toHaveAttribute("data-cover-status", "ready");
  await expect(page.getByTestId("viewer-cover-image")).toHaveAttribute("src", /assets\/covers\/manifest-cover\.png/);
  expect(localCoverRequests).toBeGreaterThan(0);
  expect(signals.failedCoverRequests).toEqual([]);
  expectNoRuntimeErrors(signals);
});

test("pending cover times out to a stable placeholder without layout shift", async ({ page }) => {
  let releasePending!: () => void;
  const pending = new Promise<void>((resolve) => {
    releasePending = resolve;
  });
  await page.route(COVER_PATTERN, async (route) => {
    await pending;
    await route.abort("timedout").catch(() => undefined);
  });
  const signals = await setupPage(page);

  try {
    const { visibleAfterMs } = await openViewer(page);
    expect(visibleAfterMs).toBeLessThan(2500);
    await expect(page.getByTestId("viewer-cover-frame")).toHaveAttribute("data-cover-status", "loading");
    await page.waitForTimeout(500);
    const before = await page.getByTestId("viewer-cover-frame").boundingBox();
    await expect(page.getByTestId("viewer-cover-frame")).toHaveAttribute("data-cover-status", "failed", {
      timeout: 6500
    });
    await expect(page.getByTestId("viewer-cover-placeholder")).toBeVisible();
    await expectStableLayout(page, before);
    expectNoRuntimeErrors(signals);
  } finally {
    releasePending();
  }
});

test("failed cover can recover after switching away and back", async ({ page }) => {
  let firstCoverAvailable = false;
  await page.route(COVER_PATTERN, async (route) => {
    if (route.request().url().includes(FIRST_VISIBLE_COVER) && !firstCoverAvailable) {
      await route.fulfill({ status: 503, contentType: "text/plain", body: "unavailable" });
      return;
    }
    await fulfillImage(route);
  });
  const signals = await setupPage(page);

  await openViewer(page);
  await expect(page.getByTestId("viewer-cover-frame")).toHaveAttribute("data-cover-status", "failed");
  expect(signals.failedCoverResponses).toContain(503);

  firstCoverAvailable = true;
  await page.keyboard.press("ArrowRight");
  await expect(page.getByRole("dialog", { name: "Album 8" })).toBeVisible();
  await expect(page.getByTestId("viewer-cover-image")).toHaveAttribute("alt", "Album 8 cover");
  await page.keyboard.press("ArrowLeft");
  await expect(page.getByRole("dialog", { name: "Album 7" })).toBeVisible();
  await expect(page.getByTestId("viewer-cover-frame")).toHaveAttribute("data-cover-status", "ready");
  await expect(page.getByTestId("viewer-cover-image")).toHaveAttribute("alt", "Album 7 cover");
  expectNoRuntimeErrors(signals);
});

test("late old cover cannot block or pollute the newly selected album", async ({ page }) => {
  let releaseFirst!: () => void;
  const firstPending = new Promise<void>((resolve) => {
    releaseFirst = resolve;
  });
  await page.route(COVER_PATTERN, async (route) => {
    if (route.request().url().includes(FIRST_VISIBLE_COVER)) {
      await firstPending;
      await fulfillImage(route).catch(() => undefined);
      return;
    }
    await fulfillImage(route);
  });
  const signals = await setupPage(page);

  try {
    await openViewer(page);
    await expect(page.getByTestId("viewer-cover-frame")).toHaveAttribute("data-cover-status", "loading");
    await page.keyboard.press("ArrowRight");
    await expect(page.getByRole("dialog", { name: "Album 8" })).toBeVisible();
    await expect(page.getByTestId("viewer-cover-image")).toHaveAttribute("alt", "Album 8 cover");
    const secondSrc = await page.getByTestId("viewer-cover-image").getAttribute("src");
    expect(secondSrc).toContain(SECOND_VISIBLE_COVER);

    releaseFirst();
    await page.waitForTimeout(250);
    await expect(page.getByRole("dialog", { name: "Album 8" })).toBeVisible();
    await expect(page.getByTestId("viewer-cover-image")).toHaveAttribute("src", /cover-7/);
    expectNoRuntimeErrors(signals);
  } finally {
    releaseFirst();
  }
});
