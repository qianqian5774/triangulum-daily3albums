import { expect, test, type Page } from "@playwright/test";

async function buildDate(page: Page) {
  const response = await page.request.get("/data/today.json");
  expect(response.ok()).toBe(true);
  const payload = await response.json();
  expect(typeof payload.date).toBe("string");
  return payload.date as string;
}

async function visitTodayAt(page: Page, width: number, height: number) {
  await page.setViewportSize({ width, height });
  await page.addInitScript(() => {
    window.localStorage.setItem("tri_ui_font_scale", "1.56");
  });
  const date = await buildDate(page);
  await page.goto(`/#/?debug=1&debug_time=${date}T18:00:00`);
  await page.waitForSelector('[data-testid="album-card-0"]', { state: "visible" });
}

async function expectNoPageHorizontalOverflow(page: Page) {
  const result = await page.evaluate(() => {
    const root = document.documentElement;
    const viewportWidth = root.clientWidth;
    const overflowDelta = root.scrollWidth - viewportWidth;
    const clipsInlineOverflow = (element: HTMLElement) => {
      let current = element.parentElement;
      while (current && current !== document.body) {
        const style = window.getComputedStyle(current);
        if (["auto", "clip", "hidden", "scroll"].includes(style.overflowX)) {
          const rect = current.getBoundingClientRect();
          return rect.left >= -1 && rect.right <= viewportWidth + 1;
        }
        current = current.parentElement;
      }
      return false;
    };
    const offenders = Array.from(document.body.querySelectorAll<HTMLElement>("*"))
      .map((element) => {
        const rect = element.getBoundingClientRect();
        return {
          tag: element.tagName.toLowerCase(),
          className: String(element.className || ""),
          left: rect.left,
          right: rect.right,
          width: rect.width,
          clippedByAncestor: clipsInlineOverflow(element)
        };
      })
      .filter(
        (item) =>
          item.width > 1 &&
          !item.clippedByAncestor &&
          (item.left < -1 || item.right > viewportWidth + 1)
      )
      .slice(0, 8);
    return { overflowDelta, offenders, viewportWidth };
  });

  expect(result.overflowDelta, JSON.stringify(result, null, 2)).toBeLessThanOrEqual(1);
  expect(result.offenders, JSON.stringify(result, null, 2)).toHaveLength(0);
}

async function expectHudControlsFit(page: Page) {
  const result = await page.locator('[data-testid="hud"]').evaluate((hud) => {
    const hudRect = hud.getBoundingClientRect();
    const controls = Array.from(hud.querySelectorAll<HTMLElement>("a, button"));
    const offenders = controls
      .map((element) => {
        const rect = element.getBoundingClientRect();
        return {
          text: element.innerText,
          className: String(element.className || ""),
          left: rect.left,
          right: rect.right,
          hudLeft: hudRect.left,
          hudRight: hudRect.right,
          width: rect.width
        };
      })
      .filter(
        (item) =>
          item.width > 1 &&
          (item.left < hudRect.left - 1 || item.right > hudRect.right + 1)
      );
    return { hudLeft: hudRect.left, hudRight: hudRect.right, offenders };
  });

  expect(result.offenders, JSON.stringify(result, null, 2)).toHaveLength(0);
}

test("desktop HUD remains fixed", async ({ page }) => {
  await visitTodayAt(page, 1280, 720);
  await expectNoPageHorizontalOverflow(page);
  await expectHudControlsFit(page);

  const hudPosition = await page.locator('[data-testid="hud"]').evaluate((element) => {
    return window.getComputedStyle(element).position;
  });
  expect(hudPosition).toBe("fixed");
});

for (const width of [360, 390, 430]) {
  test(`mobile layout has no page overflow at A+ width ${width}`, async ({ page }) => {
    await visitTodayAt(page, width, width === 360 ? 780 : 844);

    const hudPosition = await page.locator('[data-testid="hud"]').evaluate((element) => {
      return window.getComputedStyle(element).position;
    });
    expect(hudPosition).not.toBe("fixed");
    await expectNoPageHorizontalOverflow(page);
    await expectHudControlsFit(page);

    await page.click('[data-testid="album-card-0"]');
    const overlay = page.locator('[data-testid="treatment-overlay"]');
    await overlay.waitFor({ state: "visible" });
    await expectNoPageHorizontalOverflow(page);

    const overlayBox = await overlay.boundingBox();
    expect(overlayBox).not.toBeNull();
    expect(overlayBox!.x).toBeGreaterThanOrEqual(0);
    expect(overlayBox!.x + overlayBox!.width).toBeLessThanOrEqual(width);
  });
}
