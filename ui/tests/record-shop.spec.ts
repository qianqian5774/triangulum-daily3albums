import { expect, test, type Page } from "@playwright/test";

const date = "2026-07-13";
const historyDate = "2026-01-19";

async function openShopAt(page: Page, time: string) {
  await page.goto(`/#/?debug=1&debug_time=${date}T${time}`);
  await expect(page.getByRole("main", { name: "Triangulum Daily record shop" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Triangulum Daily Entry Diorama" })).toBeVisible();
  await expect(page.locator(".entry-diorama")).toHaveAttribute("data-ready", "true");
}

async function enterGallery(page: Page) {
  await page.getByRole("button", { name: "Open the physical entrance door to enter the Public Record Gallery" }).click();
  await expect(page.getByRole("region", { name: "Daily Device" })).toBeVisible();
}

async function revealInventory(page: Page) {
  const open = page.getByRole("button", { name: "OPEN", exact: true });
  if (await open.count()) {
    await open.click();
    const play = page.getByRole("button", { name: "PLAY", exact: true });
    if (await play.count()) await play.click();
    const complete = page.getByRole("region", { name: "Trigger complete" });
    await expect(complete).toBeVisible({ timeout: 4_000 });
    await complete.getByRole("button", { name: "CONTINUE", exact: true }).click();
  }
  await expect(page.getByRole("region", { name: "Today record inventory" })).toBeVisible();
}

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
  });
});

test("formal exterior exposes only the six approved views and crosses the real door", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await openShopAt(page, "08:00:00");

  await expect(page.locator(".entry-diorama")).toHaveAttribute("data-model", "procedural-geometry");
  await expect(page.getByText("OPEN DOOR", { exact: true })).toHaveCount(0);
  await expect(page.getByText("CLICK THE DOOR TO ENTER", { exact: true })).toBeVisible();
  await expect(page.getByText("VIEWS", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "PROJECT INFO", exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "DAILY RHYTHM", exact: true })).toBeVisible();
  await expect(page.getByText("TODAY · 3 / 9 RECORDS AVAILABLE", { exact: true })).toBeVisible();
  const exteriorResources = await page.evaluate(() => performance.getEntriesByType("resource").map((entry) => entry.name));
  expect(exteriorResources.some((resource) => /entry-diorama-(front|right|rear|left)\./.test(resource))).toBe(false);

  const views = page.getByRole("navigation", { name: "Approved exterior camera views" }).getByRole("button");
  await expect(views).toHaveCount(6);
  const front = page.getByRole("button", { name: "FRONT ELEVATION" });
  await front.click();
  await expect(front).toHaveAttribute("aria-pressed", "true");

  await enterGallery(page);
  await expect(page.getByRole("button", { name: "OPEN", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "RETURN TO ENTRY" }).click();
  await expect(front).toHaveAttribute("aria-pressed", "true");
});

test("entry information overlays and debug replay stay lightweight and recoverable", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await openShopAt(page, "16:00:00");

  await page.getByRole("button", { name: "PROJECT INFO", exact: true }).click();
  const info = page.getByRole("dialog");
  await expect(info).toContainText("Triangulum Daily is a daily album recommendation experience that opens gradually across three Beijing Time windows.");
  await expect(info).toContainText("08:00");
  await expect(info).toContainText("+3 records");
  await info.getByRole("button", { name: "CLOSE ×" }).click();
  await expect(info).toBeHidden();

  await page.getByRole("button", { name: "DAILY RHYTHM", exact: true }).click();
  await expect(page.getByRole("dialog")).toContainText("00:00–07:59");
  await expect(page.getByRole("dialog")).toContainText("CLOSED");
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toBeHidden();

  await page.getByRole("button", { name: "TIME DEBUG" }).click();
  await page.getByRole("button", { name: "RUN ENTRY", exact: true }).click();
  await expect(page.getByRole("region", { name: "Daily Device" })).toBeVisible();
  await page.getByRole("button", { name: "RETURN TO ENTRY" }).click();
  await expect(page.locator(".entry-diorama")).toHaveAttribute("data-ready", "true");
  await page.waitForTimeout(120);
  await expect(page.locator(".entry-diorama")).not.toHaveAttribute("data-entering", "true");
  await expect(page.getByRole("button", { name: "RESET ENTRY", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "RESET ENTRY", exact: true }).click();
  await expect(page.locator(".entry-diorama")).toHaveAttribute("data-view", "front");
  await expect(page.getByRole("region", { name: "Triangulum Daily Entry Diorama" })).toBeVisible();
});

test("exterior view changes use one canvas and support bounded wheel and button zoom", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await openShopAt(page, "08:00:00");

  const runtimeErrors: string[] = [];
  page.on("pageerror", (error) => runtimeErrors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") runtimeErrors.push(message.text());
  });

  const viewButtons = page.getByRole("navigation", { name: "Approved exterior camera views" }).getByRole("button");
  for (const label of ["REAR ELEVATION", "LEFT ELEVATION", "RIGHT ELEVATION", "ROOF PLAN", "AXONOMETRIC", "FRONT ELEVATION"]) {
    await page.getByRole("button", { name: label }).click();
  }
  await expect(viewButtons).toHaveCount(6);
  await expect(page.locator(".entry-diorama canvas")).toHaveCount(1);
  await expect(page.locator(".entry-diorama")).toHaveAttribute("data-view", "front");

  const diorama = page.locator(".entry-diorama");
  const zoom = page.locator(".entry-diorama__zoom");
  await expect(diorama).toHaveAttribute("data-zoom", "1.00");
  await zoom.getByRole("button", { name: "Zoom in exterior model" }).click();
  await expect(diorama).toHaveAttribute("data-zoom", "1.12");
  await zoom.getByRole("button", { name: "Reset model zoom" }).click();
  await page.locator(".entry-diorama__canvas canvas").dispatchEvent("wheel", { deltaY: 100 });
  await expect(diorama).toHaveAttribute("data-zoom", "0.90");
  await zoom.getByRole("button", { name: "Reset model zoom" }).click();
  for (let index = 0; index < 20; index += 1) await zoom.getByRole("button", { name: "Zoom in exterior model" }).click();
  await expect(diorama).toHaveAttribute("data-zoom", "1.12");
  for (let index = 0; index < 40; index += 1) await zoom.getByRole("button", { name: "Zoom out exterior model" }).click();
  await expect(diorama).toHaveAttribute("data-zoom", "0.90");
  await zoom.getByRole("button", { name: "Reset model zoom" }).click();
  await expect(diorama).toHaveAttribute("data-zoom", "1.00");
  expect(runtimeErrors).toEqual([]);
});

test("the exterior can orbit freely and every preset restores a stable authored view", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await openShopAt(page, "16:00:00");
  const canvas = page.locator(".entry-diorama canvas");
  const frame = page.locator(".entry-diorama__canvas");
  const bounds = await canvas.boundingBox();
  expect(bounds).not.toBeNull();
  const before = await frame.screenshot();
  await page.mouse.move(bounds!.x + bounds!.width * .72, bounds!.y + bounds!.height * .38);
  await page.mouse.down();
  await page.mouse.move(bounds!.x + bounds!.width * .55, bounds!.y + bounds!.height * .31, { steps: 8 });
  await page.mouse.up();
  await page.waitForTimeout(80);
  const orbited = await frame.screenshot();
  const upwardDragElevation = Number(await canvas.getAttribute("data-orbit-elevation"));
  expect(orbited.equals(before)).toBe(false);
  await page.getByRole("button", { name: "AXONOMETRIC", exact: true }).click();
  await page.mouse.move(bounds!.x + bounds!.width * .72, bounds!.y + bounds!.height * .31);
  await page.mouse.down();
  await page.mouse.move(bounds!.x + bounds!.width * .55, bounds!.y + bounds!.height * .45, { steps: 8 });
  await page.mouse.up();
  const downwardDragElevation = Number(await canvas.getAttribute("data-orbit-elevation"));
  expect(downwardDragElevation).toBeGreaterThan(upwardDragElevation);
  await page.getByRole("button", { name: "AXONOMETRIC", exact: true }).click();
  await page.waitForTimeout(80);
  const restored = await frame.screenshot();
  await page.waitForTimeout(120);
  const settled = await frame.screenshot();
  expect(settled.equals(restored)).toBe(true);
});

test("settled exterior frames remain stable without geometry-edge flicker", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await openShopAt(page, "16:00:00");
  const canvasRegion = page.locator(".entry-diorama__canvas");

  for (const label of ["AXONOMETRIC", "FRONT ELEVATION", "RIGHT ELEVATION", "REAR ELEVATION", "LEFT ELEVATION", "ROOF PLAN"]) {
    await page.getByRole("button", { name: label }).click();
    await page.waitForTimeout(80);
    const first = await canvasRegion.screenshot();
    await page.waitForTimeout(120);
    const second = await canvasRegion.screenshot();
    expect(first.equals(second), `${label} changed between settled frames`).toBe(true);
  }
});

test("sound is opt-in, gesture-enabled, and persists across the exterior-interior handoff", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 720 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await openShopAt(page, "16:00:00");
  const sound = page.getByRole("button", { name: "Enable ambient sound and interface cues" });
  await expect(sound).toHaveAttribute("aria-pressed", "false");
  await sound.click();
  const mute = page.getByRole("button", { name: "Mute ambient sound and interface cues" });
  await expect(mute).toHaveAttribute("aria-pressed", "true");
  await enterGallery(page);
  await expect(mute).toHaveAttribute("aria-pressed", "true");
  await mute.click();
  await expect(page.getByRole("button", { name: "Enable ambient sound and interface cues" })).toHaveAttribute("aria-pressed", "false");
});

for (const [time, count] of [["08:00:00", 3], ["12:30:00", 6], ["16:00:00", 9]] as const) {
  test(`the ${time} BJT window exposes exactly ${count} records`, async ({ page }) => {
    await page.setViewportSize({ width: 1280, height: 720 });
    await page.emulateMedia({ reducedMotion: "reduce" });
    await openShopAt(page, time);
    await enterGallery(page);
    await revealInventory(page);
    await expect(page.locator(".record-shop__spine")).toHaveCount(count);
  });
}

test("inventory reads published title, artist, role, and cover fallback fields", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 720 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await openShopAt(page, "16:00:00");
  await enterGallery(page);
  await revealInventory(page);

  const firstRecord = page.locator(".record-shop__spine").first();
  await expect(firstRecord).toHaveAttribute("data-role", "Headliner");
  await expect(firstRecord).toHaveAttribute("data-slot-id", "0");
  await expect(firstRecord).toContainText("The Downward Spiral");
  await firstRecord.click();
  const treatment = page.getByRole("dialog");
  await expect(treatment).toContainText("The Downward Spiral");
  await expect(treatment).toContainText("Nine Inch Nails");
  await expect(treatment.locator(".gallery-art__cover")).toHaveAttribute("src", /assets\/placeholder\.svg/);
  await expect(treatment).toContainText("PUBLISHED STATIC ISSUE");
});

test("the device panel closes, reopens, and responds to Escape", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await openShopAt(page, "16:00:00");
  await enterGallery(page);
  await revealInventory(page);

  const inventory = page.getByRole("region", { name: "Today record inventory" });
  await page.getByRole("button", { name: "Close Daily Device" }).click();
  await expect(inventory).toBeHidden();
  await expect(page.locator(".record-shop")).toHaveAttribute("data-device-panel", "closed");
  await page.getByRole("button", { name: "VIEW RECORDS", exact: true }).click();
  await expect(inventory).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(inventory).toBeHidden();
});

test("time debugger exposes day, night, unlock counts, and real clock", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await openShopAt(page, "21:00:00");
  await expect(page.locator(".entry-diorama")).toHaveAttribute("data-theme", "night");
  await page.getByRole("button", { name: "TIME DEBUG" }).click();
  await page.getByRole("button", { name: "08:00 · DAY · 3" }).click();
  await expect(page.locator(".entry-diorama")).toHaveAttribute("data-theme", "day");
  await page.getByRole("button", { name: "TIME DEBUG" }).click();
  await page.getByRole("button", { name: "REAL TIME" }).click();
  await page.getByRole("button", { name: "TIME DEBUG" }).click();
  await expect(page.getByText("REAL CLOCK", { exact: true })).toBeVisible();
});

test("treatment, recent-date history, and return-to-Today remain overlays and states", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await openShopAt(page, "16:00:00");
  await enterGallery(page);
  await revealInventory(page);

  await page.locator(".record-shop__spine").first().click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.getByRole("button", { name: "BACK TO SPINES", exact: true }).click();
  await expect(page.getByRole("dialog")).toBeHidden();

  await page.getByRole("button", { name: new RegExp(`DATE\\s+${date.slice(5)}`) }).click();
  await page.getByRole("option", { name: `${historyDate.slice(5)} HISTORY` }).click();
  await expect(page.getByRole("region", { name: "Historical record inventory" })).toBeVisible();
  await expect(page.locator(".record-shop__spine")).toHaveCount(3);
  await page.getByRole("button", { name: "RETURN TO TODAY" }).click();
  await expect(page.getByRole("region", { name: "Today record inventory" })).toBeVisible();
});

test("English and Chinese cover the exterior, information, HUD, device, history, and utility states", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await openShopAt(page, "16:00:00");

  await page.getByRole("button", { name: "中文", exact: true }).click();
  await expect(page.getByRole("region", { name: "Triangulum Daily 入口微缩模型" })).toBeVisible();
  await expect(page.getByText("点击大门进入店内", { exact: true })).toBeVisible();
  await expect(page.getByText("今日 · 9 / 9 张唱片已开放", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "项目说明", exact: true }).click();
  await expect(page.getByRole("dialog")).toContainText("按北京时间三个时段逐步开放");
  await page.keyboard.press("Escape");

  await page.getByRole("button", { name: "打开实体大门，进入唱片陈列室" }).click();
  await expect(page.getByRole("region", { name: "店内状态吊牌" })).toContainText("设备");
  await expect(page.getByRole("region", { name: "DAILY DEVICE" })).toContainText("本时段已就绪");
  await page.getByRole("button", { name: /日期\s+07-13/ }).click();
  await page.getByRole("option", { name: `${historyDate.slice(5)} 历史` }).click();
  await expect(page.getByRole("region", { name: "历史唱片库存" })).toBeVisible();
  await expect(page.getByRole("button", { name: "返回今日" })).toBeVisible();
  await page.locator(".record-shop__spine").first().click();
  await expect(page.getByRole("dialog")).toContainText("The Downward Spiral");
  await expect(page.getByRole("dialog")).toContainText("Nine Inch Nails");
  await expect(page.getByRole("dialog")).not.toContainText("本地唱片目录预览");
  await page.getByRole("button", { name: "返回唱片书脊", exact: true }).click();

  await page.getByRole("button", { name: "EN", exact: true }).click();
  await expect(page.getByRole("region", { name: "Historical record inventory" })).toBeVisible();
  await expect(page.getByRole("button", { name: "RETURN TO TODAY" })).toBeVisible();
  await page.locator(".record-shop__spine").first().click();
  await expect(page.getByRole("dialog")).toContainText("The Downward Spiral");
  await expect(page.getByRole("dialog")).not.toContainText("LOCAL CATALOGUE PREVIEW");
});

test("the shared language preference also covers the Today and Archive routes", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto(`/#/today?debug=1&debug_time=${date}T16:00:00`);
  await expect(page.getByTestId("hud")).toBeVisible();

  await page.getByRole("button", { name: "中文", exact: true }).click();
  await expect(page.getByRole("link", { name: "今日", exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "历史", exact: true })).toBeVisible();
  await expect(page.getByText("每日九张专辑，分三轮信号窗口释放，避开惯常推荐回路。", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "项目说明", exact: true }).click();
  await expect(page.getByRole("dialog")).toContainText("每天发布九张专辑推荐");
  await page.getByRole("dialog").getByRole("button", { name: "关闭", exact: true }).click();

  await page.getByRole("link", { name: "历史", exact: true }).click();
  await expect(page.getByRole("heading", { name: "最近历史" })).toBeVisible();
  await page.getByRole("button", { name: "EN", exact: true }).click();
  await expect(page.getByRole("heading", { name: "RECENT ARCHIVE" })).toBeVisible();
});

test("the hanging HUD is one DOM object and the environment carries no baked HUD layer", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await openShopAt(page, "12:30:00");
  await enterGallery(page);

  const hud = page.getByTestId("interior-hud");
  await expect(hud).toBeVisible();
  await expect(hud.locator(".record-shop__hud-rod")).toHaveCount(2);
  await expect(hud.locator(".record-shop__hud-bezel")).toHaveCount(1);
  await expect(hud.locator(".record-shop__hud-glass")).toHaveCount(1);
  await expect(page.locator(".record-shop__hud-shell")).toHaveCount(0);
  await expect(page.locator(".record-shop__environment")).toHaveAttribute("src", /environment-device-integrated-day-no-hud-v3/);

  const before = await page.locator(".record-shop__environment").isVisible();
  const hideHud = await page.addStyleTag({ content: ".record-shop__interior-hud { display: none !important; }" });
  expect(before).toBe(true);
  await expect(page.locator(".record-shop__environment")).toBeVisible();
  await expect(hud).toBeHidden();
  await hideHud.evaluate((node) => node.remove());
  await expect(hud).toBeVisible();
});

test("door opening, approach, and threshold crossing are ordered before the interior arrives", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await openShopAt(page, "16:00:00");

  const diorama = page.locator(".entry-diorama");
  await page.getByRole("button", { name: "Open the physical entrance door to enter the Public Record Gallery" }).click();
  await expect(diorama).toHaveAttribute("data-entry-phase", "opening");
  await expect.poll(() => diorama.getAttribute("data-entry-phase"), { timeout: 1_200 }).toBe("approaching");
  await expect.poll(() => diorama.getAttribute("data-entry-phase"), { timeout: 1_300 }).toBe("crossing");
  await expect(page.getByRole("region", { name: "Daily Device" })).toBeVisible({ timeout: 2_000 });
});

test("canvas pixel ratio is requantized across browser scale factors", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await openShopAt(page, "08:00:00");
  const canvas = page.locator(".entry-diorama canvas");

  for (const [scale, expected] of [[0.5, "1.00"], [1, "1.00"], [1.5, "1.50"], [2, "2.00"], [3, "2.00"]] as const) {
    await page.evaluate((nextScale) => {
      Object.defineProperty(window, "devicePixelRatio", { configurable: true, value: nextScale });
      window.dispatchEvent(new Event("resize"));
      window.visualViewport?.dispatchEvent(new Event("resize"));
    }, scale);
    await expect.poll(() => canvas.getAttribute("data-pixel-ratio"), { timeout: 2_000 }).toBe(expected);
  }
});

test("common 50 to 300 percent browser-zoom layout equivalents stay bounded", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await openShopAt(page, "16:00:00");

  for (const [zoom, width, height] of [[50, 2880, 1800], [100, 1440, 900], [150, 960, 600], [200, 720, 450], [300, 480, 300]] as const) {
    await page.setViewportSize({ width, height });
    await expect(page.locator(".entry-diorama")).toHaveAttribute("data-ready", "true");
    const geometry = await page.evaluate(() => ({
      horizontal: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      vertical: document.documentElement.scrollHeight - document.documentElement.clientHeight,
      canvasWidth: document.querySelector(".entry-diorama canvas")?.getBoundingClientRect().width ?? 0,
      canvasHeight: document.querySelector(".entry-diorama canvas")?.getBoundingClientRect().height ?? 0
    }));
    expect(geometry.horizontal, `${zoom}% horizontal overflow`).toBeLessThanOrEqual(1);
    expect(geometry.vertical, `${zoom}% vertical overflow`).toBeLessThanOrEqual(1);
    expect(geometry.canvasWidth).toBeGreaterThan(0);
    expect(geometry.canvasHeight).toBeGreaterThan(0);
  }

  await enterGallery(page);
  const hudBox = await page.getByTestId("interior-hud").boundingBox();
  expect(hudBox).not.toBeNull();
  expect(hudBox!.x).toBeGreaterThanOrEqual(0);
  expect(hudBox!.x + hudBox!.width).toBeLessThanOrEqual(481);
  expect(hudBox!.y + hudBox!.height).toBeLessThanOrEqual(301);
  const geometry = await page.evaluate(() => ({
    horizontal: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    vertical: document.documentElement.scrollHeight - document.documentElement.clientHeight
  }));
  expect(geometry.horizontal).toBeLessThanOrEqual(1);
  expect(geometry.vertical).toBeLessThanOrEqual(1);
});

test("the device remains unavailable before 08:00", async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 720 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await openShopAt(page, "07:59:00");
  await enterGallery(page);
  await expect(page.getByRole("region", { name: "Daily Device" })).toContainText("OFFLINE");
  await expect(page.getByRole("button", { name: "OPEN", exact: true })).toHaveCount(0);
  await expect(page.locator(".record-shop__spine")).toHaveCount(0);
});

test("the complete flow has no narrow-screen overflow", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await openShopAt(page, "16:00:00");
  await enterGallery(page);
  await revealInventory(page);
  await page.locator(".record-shop__spine").first().click();
  await expect(page.getByRole("dialog")).toBeVisible();

  const geometry = await page.evaluate(() => ({
    horizontal: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    vertical: document.documentElement.scrollHeight - document.documentElement.clientHeight
  }));
  expect(geometry.horizontal).toBeLessThanOrEqual(1);
  expect(geometry.vertical).toBeLessThanOrEqual(1);
});

test("browser Ctrl-wheel is not consumed by the diorama camera", async ({ page }) => {
  await openShopAt(page, "16:00:00");
  const result = await page.locator(".entry-diorama canvas").evaluate((canvas) => {
    const wheel = new WheelEvent("wheel", { deltaY: -400, ctrlKey: true, bubbles: true, cancelable: true });
    canvas.dispatchEvent(wheel);
    return wheel.defaultPrevented;
  });
  expect(result).toBe(false);
  await expect(page.locator(".entry-diorama")).toHaveAttribute("data-zoom", "1.00");
});

test("entry waits for decoded interior assets before beginning the threshold sequence", async ({ page }) => {
  await page.addInitScript(() => {
    const nativeDecode = HTMLImageElement.prototype.decode;
    let release!: () => void;
    const gate = new Promise<void>((resolve) => { release = resolve; });
    (window as Window & { __releaseInteriorDecode?: () => void }).__releaseInteriorDecode = release;
    HTMLImageElement.prototype.decode = function decodeWithGate() {
      if (this.src.includes("environment-device-integrated-day-no-hud-v3")) return gate.then(() => nativeDecode.call(this));
      return nativeDecode.call(this);
    };
  });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await openShopAt(page, "16:00:00");
  const door = page.getByRole("button", { name: "Open the physical entrance door to enter the Public Record Gallery" });
  await expect(door).toBeDisabled();
  await page.evaluate(() => (window as Window & { __releaseInteriorDecode?: () => void }).__releaseInteriorDecode?.());
  await expect(door).toBeEnabled();
  await door.click();
  await expect(page.locator(".record-shop__environment")).toBeVisible();
  expect(await page.locator(".record-shop__environment").evaluate((image) => (image as HTMLImageElement).naturalWidth)).toBe(1680);
  await expect(page.locator(".record-shop-loading")).toHaveCount(0);
});

test("HUD readout and progress never overlap or block the date control in either language", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await openShopAt(page, "12:30:00");
  await enterGallery(page);
  for (const [width, height] of [[1440, 900], [960, 600], [720, 450], [480, 300], [390, 844]]) {
    await page.setViewportSize({ width, height });
    for (const language of ["EN", "中文"]) {
      await page.getByRole("button", { name: language, exact: true }).click();
      const geometry = await page.evaluate(() => {
        const readout = document.querySelector(".record-shop__hud-readout")!.getBoundingClientRect();
        const progress = document.querySelector(".record-shop__hud-progress")!;
        const hud = document.querySelector(".record-shop__interior-hud")!.getBoundingClientRect();
        const button = document.querySelector(".record-shop__hud-date")!;
        const b = button.getBoundingClientRect();
        return {
          overlap: getComputedStyle(progress).display === "none" ? 0 : Math.max(0, readout.bottom - progress.getBoundingClientRect().top),
          hit: button.contains(document.elementFromPoint(b.x + b.width / 2, b.y + b.height / 2)),
          right: hud.right, bottom: hud.bottom
        };
      });
      expect(geometry.overlap, `${language} ${width}`).toBeLessThanOrEqual(1);
      expect(geometry.hit, `${language} ${width} date hit region`).toBe(true);
      expect(geometry.right).toBeLessThanOrEqual(width + 1);
      expect(geometry.bottom).toBeLessThanOrEqual(height + 1);
    }
  }
});

test("the shop sign follows unlock state without replacing the canvas", async ({ page }) => {
  await openShopAt(page, "07:59:00");
  await expect(page.locator(".entry-diorama")).toHaveAttribute("data-life", "quiet");
  await page.getByRole("button", { name: "TIME DEBUG" }).click();
  await page.getByRole("button", { name: "08:00 · DAY · 3", exact: true }).click();
  await expect(page.locator(".entry-diorama")).toHaveAttribute("data-life", "open");
  // 08:00 also changes night to day, so subsequent releases keep that canvas.
  const dayCanvas = await page.locator(".entry-diorama canvas").elementHandle();
  await page.getByRole("button", { name: "TIME DEBUG" }).click();
  await page.getByRole("button", { name: "12:30 · DAY · 6", exact: true }).click();
  expect(await dayCanvas!.evaluate(node => node.isConnected)).toBe(true);
  await expect(page.getByText("TODAY · 6 / 9 RECORDS AVAILABLE", { exact: true })).toBeVisible();
  await dayCanvas?.dispose();
});
