import { expect, test } from "@playwright/test";

const issueDate = "2026-07-13";

// Local visual evidence remains under the configured ignored artifact folder.
for (const language of ["en", "zh"]) for (const size of ["desktop", "enlarged", "phone"]) {
  test(`authored day/night scene and inventory: ${language}, ${size}`, async ({ page }, testInfo) => {
    const errors: string[] = [];
    page.on("pageerror", error => errors.push(error.message));
    await page.addInitScript(language => { localStorage.clear(); localStorage.setItem("tri_ui_language", language); }, language);
    await page.setViewportSize(size === "phone" ? { width: 390, height: 844 } : size === "enlarged" ? { width: 960, height: 600 } : { width: 1440, height: 900 });
    await page.emulateMedia({ reducedMotion: "reduce" });
    for (const [theme, time] of [["day", "16:00:00"], ["night", "21:00:00"]]) {
      await page.goto(`/#/?debug=1&debug_time=${issueDate}T${time}`);
      await expect(page.locator(".entry-diorama")).toHaveAttribute("data-ready", "true");
      await page.locator(".entry-diorama__door").click();
      await expect(page.locator(".record-shop")).toHaveAttribute("data-environment", theme);
      const environment = page.locator(".record-shop__environment");
      await expect(environment).toHaveAttribute("src", new RegExp(`environment-device-integrated-${theme}-no-hud-v3`));
      expect(await environment.evaluate(image => (image as HTMLImageElement).complete && (image as HTMLImageElement).naturalWidth >= 1600)).toBe(true);
      await expect(page.locator(".record-shop__screen-bezel")).toHaveCount(1);
      await expect(page.locator(".record-shop__attendant")).toHaveCount(1);
      await expect(page.locator(".record-shop__counter")).toHaveCount(1);
      await expect(page.locator(".record-shop__hand-shadow")).toHaveCount(1);
      await expect(page.locator(".record-shop__hands")).toHaveCount(1);
      const hud = page.locator(".record-shop__interior-hud");
      expect(await hud.evaluate(node => node.scrollWidth <= node.clientWidth + 1)).toBe(true);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
      await page.screenshot({ path: testInfo.outputPath(`${theme}-arrival.png`) });
      if (size === "desktop" && language === "zh") {
        await hud.evaluate(node => { (node as HTMLElement).style.visibility = "hidden"; });
        await page.screenshot({ path: testInfo.outputPath(`${theme}-without-hud.png`) });
        await hud.evaluate(node => { (node as HTMLElement).style.visibility = ""; });
      }
      await hud.locator("button").first().click();
      await expect(page.getByRole("listbox")).toBeVisible();
      await page.screenshot({ path: testInfo.outputPath(`${theme}-history-menu.png`) });
      await page.getByRole("option").nth(1).click();
      await expect(page.locator(".record-shop__device-panel")).toHaveAttribute("data-record-count", "3");
      await page.screenshot({ path: testInfo.outputPath(`${theme}-history-inventory.png`) });
      await page.locator(".record-shop__spine").first().click();
      await expect(page.locator(".gallery-treatment")).toBeVisible();
      await page.screenshot({ path: testInfo.outputPath(`${theme}-treatment.png`) });
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
      await page.reload();
    }
    expect(errors).toEqual([]);
  });
}

test("idle exterior stops drawing; retained asset decoding and language do not rebuild the renderer", async ({ page }, testInfo) => {
  await page.addInitScript(() => { localStorage.clear(); });
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(`/#/?debug=1&debug_time=${issueDate}T16:00:00`);
  await expect(page.locator(".entry-diorama")).toHaveAttribute("data-ready", "true");
  const canvas = page.locator(".entry-diorama canvas");
  const start = await canvas.getAttribute("data-render-count");
  test.skip(start === null, "Detailed renderer counters exist only in the local Vite build.");
  await page.waitForTimeout(1200);
  expect(await canvas.getAttribute("data-render-count")).toBe(start);
  const identity = await canvas.elementHandle();
  await page.getByRole("button", { name: "中文", exact: true }).click();
  expect(await identity!.evaluate(node => node === document.querySelector(".entry-diorama canvas"))).toBe(true);
  const metrics = await canvas.evaluate(node => ({ ...(node as HTMLElement).dataset }));
  expect(Number(metrics.drawCalls)).toBeLessThan(400);
  await testInfo.attach("renderer-counters", { body: JSON.stringify(metrics, null, 2), contentType: "application/json" });
  await page.screenshot({ path: testInfo.outputPath("exterior.png") });
});
