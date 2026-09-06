import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "@playwright/test";

const uiDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const outputDir = path.resolve(uiDir, "artifacts", "performance");
const baseUrl = (process.env.PERF_BASE_URL || "https://triangulumdaily.space/").replace(/\/+$/, "");
const cpuRate = Number(process.env.PERF_CPU_RATE || "4");
const settleMs = Number(process.env.PERF_SETTLE_MS || "1800");
const fpsSampleMs = Number(process.env.PERF_FPS_SAMPLE_MS || "2400");
const browserChannel = process.env.PERF_BROWSER_CHANNEL || "chrome";
const requestedScenarios = new Set(
  (process.env.PERF_SCENARIOS || "")
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean)
);

function shouldRun(name) {
  return requestedScenarios.size === 0 || requestedScenarios.has(name);
}

function bjtDate() {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
    day: "2-digit"
  }).formatToParts(new Date());
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${values.year}-${values.month}-${values.day}`;
}

const auditDate = process.env.PERF_DATE || bjtDate();
const todayUrl = `${baseUrl}/#/?debug=1&debug_time=${auditDate}T16:00:00`;
const archiveUrl = `${baseUrl}/#/archive`;

const instrumentation = () => {
  const state = {
    cls: 0,
    layoutShifts: [],
    lcp: 0,
    longTasks: [],
    events: [],
    intervalsCreated: 0,
    animationFramesScheduled: 0,
    animationFrameCallbacks: 0,
    reactCommits: 0
  };
  window.__triPerfAudit = state;

  const originalInterval = window.setInterval.bind(window);
  window.setInterval = (...args) => {
    state.intervalsCreated += 1;
    return originalInterval(...args);
  };

  const originalRaf = window.requestAnimationFrame.bind(window);
  window.requestAnimationFrame = (callback) => {
    state.animationFramesScheduled += 1;
    return originalRaf((time) => {
      state.animationFrameCallbacks += 1;
      callback(time);
    });
  };

  // Do not install a partial React DevTools hook here. Vite's React preamble
  // and the renderer expect more of that contract than a commit callback, so
  // a synthetic hook can prevent the audited page from mounting at all.
  // With no real DevTools hook present, the optional commit count stays zero.

  const observe = (type, callback, options = { type, buffered: true }) => {
    try {
      const observer = new PerformanceObserver((list) => callback(list.getEntries()));
      observer.observe(options);
    } catch {
      // Unsupported performance entry types remain explicit zero/empty values.
    }
  };

  observe("largest-contentful-paint", (entries) => {
    const latest = entries.at(-1);
    if (latest) state.lcp = latest.startTime;
  });
  observe("layout-shift", (entries) => {
    for (const entry of entries) {
      if (entry.hadRecentInput) continue;
      state.cls += entry.value;
      state.layoutShifts.push({
        startTime: entry.startTime,
        value: entry.value,
        sources: (entry.sources || []).slice(0, 5).map((source) => {
          const node = source.node;
          return {
            node:
              node instanceof Element
                ? `${node.tagName.toLowerCase()}${node.id ? `#${node.id}` : ""}${
                    node.classList.length ? `.${[...node.classList].slice(0, 3).join(".")}` : ""
                  }`
                : null,
            previousRect: source.previousRect,
            currentRect: source.currentRect
          };
        })
      });
    }
  });
  observe("longtask", (entries) => {
    state.longTasks.push(...entries.map((entry) => ({ startTime: entry.startTime, duration: entry.duration })));
  });
  observe(
    "event",
    (entries) => {
      state.events.push(
        ...entries.map((entry) => ({
          name: entry.name,
          startTime: entry.startTime,
          duration: entry.duration,
          interactionId: entry.interactionId || 0
        }))
      );
    },
    { type: "event", buffered: true, durationThreshold: 16 }
  );
};

function createNetworkTracker(cdp) {
  let requests = new Map();
  cdp.on("Network.requestWillBeSent", (event) => {
    requests.set(event.requestId, {
      url: event.request.url,
      method: event.request.method,
      type: event.type || "Other",
      status: null,
      mimeType: null,
      encodedBytes: 0,
      fromDiskCache: false,
      fromServiceWorker: false,
      failed: false
    });
  });
  cdp.on("Network.responseReceived", (event) => {
    const item = requests.get(event.requestId);
    if (!item) return;
    item.status = event.response.status;
    item.mimeType = event.response.mimeType;
    item.fromDiskCache = Boolean(event.response.fromDiskCache);
    item.fromServiceWorker = Boolean(event.response.fromServiceWorker);
  });
  cdp.on("Network.loadingFinished", (event) => {
    const item = requests.get(event.requestId);
    if (item) item.encodedBytes = event.encodedDataLength || 0;
  });
  cdp.on("Network.loadingFailed", (event) => {
    const item = requests.get(event.requestId);
    if (item) {
      item.failed = true;
      item.errorText = event.errorText;
    }
  });

  return {
    reset() {
      requests = new Map();
    },
    snapshot() {
      const rows = [...requests.values()];
      const byType = {};
      for (const row of rows) {
        const bucket = byType[row.type] || { requests: 0, encodedBytes: 0 };
        bucket.requests += 1;
        bucket.encodedBytes += row.encodedBytes;
        byType[row.type] = bucket;
      }
      return {
        requestCount: rows.length,
        encodedBytes: rows.reduce((sum, row) => sum + row.encodedBytes, 0),
        cacheHits: rows.filter((row) => row.fromDiskCache || row.fromServiceWorker).length,
        failures: rows.filter((row) => row.failed || (row.status && row.status >= 400)),
        byType,
        largest: rows
          .filter((row) => row.encodedBytes > 0)
          .sort((a, b) => b.encodedBytes - a.encodedBytes)
          .slice(0, 12)
      };
    }
  };
}

function metricMap(metrics) {
  return Object.fromEntries(metrics.map((metric) => [metric.name, metric.value]));
}

async function sampleFrames(page, durationMs) {
  return page.evaluate(async (duration) => {
    const samples = [];
    const start = performance.now();
    await new Promise((resolve) => {
      const tick = (time) => {
        samples.push(time);
        if (time - start >= duration) resolve();
        else requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    });
    const deltas = samples.slice(1).map((time, index) => time - samples[index]);
    const elapsed = samples.at(-1) - samples[0];
    return {
      sampledFrames: samples.length,
      durationMs: elapsed,
      fps: elapsed > 0 ? ((samples.length - 1) * 1000) / elapsed : 0,
      framesOver50ms: deltas.filter((delta) => delta > 50).length,
      maxFrameMs: deltas.length ? Math.max(...deltas) : 0
    };
  }, durationMs);
}

async function pageSnapshot(page) {
  return page.evaluate(() => {
    const perf = window.__triPerfAudit || {};
    const nav = performance.getEntriesByType("navigation")[0];
    const resources = performance.getEntriesByType("resource");
    const elements = [...document.querySelectorAll("body *")];
    const costly = { animated: 0, backdropFilter: 0, filter: 0, fixed: 0, willChange: 0 };
    for (const element of elements) {
      const style = getComputedStyle(element);
      if (style.animationName && style.animationName !== "none") costly.animated += 1;
      if (style.backdropFilter && style.backdropFilter !== "none") costly.backdropFilter += 1;
      if (style.filter && style.filter !== "none") costly.filter += 1;
      if (style.position === "fixed") costly.fixed += 1;
      if (style.willChange && style.willChange !== "auto") costly.willChange += 1;
    }
    const images = [...document.images].map((image) => ({
      src: image.currentSrc || image.src,
      naturalWidth: image.naturalWidth,
      naturalHeight: image.naturalHeight,
      displayWidth: image.getBoundingClientRect().width,
      displayHeight: image.getBoundingClientRect().height,
      complete: image.complete
    }));
    const eventDurations = (perf.events || []).map((entry) => entry.duration);
    return {
      title: document.title,
      domNodes: elements.length,
      overflowX: document.documentElement.scrollWidth - document.documentElement.clientWidth,
      navigation: nav
        ? {
            domContentLoadedMs: nav.domContentLoadedEventEnd,
            loadMs: nav.loadEventEnd,
            responseEndMs: nav.responseEnd,
            transferSize: nav.transferSize,
            encodedBodySize: nav.encodedBodySize,
            decodedBodySize: nav.decodedBodySize
          }
        : null,
      resourceTiming: {
        count: resources.length,
        transferSize: resources.reduce((sum, entry) => sum + (entry.transferSize || 0), 0),
        encodedBodySize: resources.reduce((sum, entry) => sum + (entry.encodedBodySize || 0), 0),
        decodedBodySize: resources.reduce((sum, entry) => sum + (entry.decodedBodySize || 0), 0)
      },
      webVitals: {
        lcpMs: perf.lcp || 0,
        cls: perf.cls || 0,
        longTaskCount: (perf.longTasks || []).length,
        longTaskTotalMs: (perf.longTasks || []).reduce((sum, entry) => sum + entry.duration, 0),
        maxLongTaskMs: (perf.longTasks || []).reduce((max, entry) => Math.max(max, entry.duration), 0),
        maxEventDurationMs: eventDurations.length ? Math.max(...eventDurations) : 0,
        largestLayoutShifts: [...(perf.layoutShifts || [])]
          .sort((a, b) => b.value - a.value)
          .slice(0, 5)
      },
      runtimeActivity: {
        intervalsCreated: perf.intervalsCreated || 0,
        animationFramesScheduled: perf.animationFramesScheduled || 0,
        animationFrameCallbacks: perf.animationFrameCallbacks || 0,
        reactCommits: perf.reactCommits || 0
      },
      costlyStyles: costly,
      images
    };
  });
}

async function waitForSurface(page, surface) {
  if (surface === "archive") {
    await page.getByRole("heading", { name: "Recent archive" }).waitFor({ state: "visible", timeout: 30000 });
  } else {
    // React may not have mounted either route by DOMContentLoaded. Wait for
    // both supported surfaces instead of making a one-time count decision.
    // The entry diorama is the formal home surface; the card remains only as
    // a compatibility fallback for generated legacy snapshots.
    const entryDiorama = page.locator(".entry-diorama");
    const legacyCard = page.getByTestId("album-card-0");
    const entryReady = entryDiorama.waitFor({ state: "visible", timeout: 30000 }).then(() => "entry").catch(() => null);
    const legacyReady = legacyCard.waitFor({ state: "visible", timeout: 30000 }).then(() => "legacy").catch(() => null);
    const arrived = await Promise.race([entryReady, legacyReady]);
    if (!arrived) throw new Error("Neither the formal entry diorama nor the legacy Today surface became visible.");
    if (arrived === "entry") {
      await entryDiorama.waitFor({ state: "visible", timeout: 30000 });
      await entryDiorama.locator("canvas").waitFor({ state: "attached", timeout: 30000 });
      return;
    }
  }
}

async function applyAction(page, action) {
  if (!action) return null;
  const started = Date.now();
  try {
    if (action === "viewer") {
      const cover = page.getByTestId("album-card-0").locator(".slotcard-cover");
      await cover.scrollIntoViewIfNeeded();
      const box = await cover.boundingBox();
      if (!box) throw new Error("album-card-0 cover has no bounding box");
      await page.mouse.click(
        box.x + Math.min(32, box.width / 4),
        box.y + Math.min(96, box.height / 3)
      );
      await page.getByTestId("treatment-overlay").waitFor({ state: "visible", timeout: 15000 });
    } else if (action === "ambient") {
      await page.getByTestId("ambient-toggle").click();
      await page
        .getByRole("dialog", { name: "Enter Ambient" })
        .waitFor({ state: "visible", timeout: 15000 });
    } else if (action === "share") {
      await page.getByTestId("share-card-toggle").click();
      await page
        .getByRole("dialog", { name: "Share Card" })
        .waitFor({ state: "visible", timeout: 15000 });
    }
    return { action, succeeded: true, visibleAfterMs: Date.now() - started };
  } catch (error) {
    return {
      action,
      succeeded: false,
      visibleAfterMs: Date.now() - started,
      error: error instanceof Error ? error.message : String(error)
    };
  }
}

async function measurePage({ browser, name, url, viewport, reducedMotion = "no-preference", action = null, warm = false }) {
  const context = await browser.newContext({ viewport, reducedMotion });
  await context.addInitScript(instrumentation);
  const page = await context.newPage();
  const browserSignals = { consoleErrors: [], consoleWarnings: [], pageErrors: [] };
  page.on("console", (message) => {
    if (message.type() === "error") browserSignals.consoleErrors.push(message.text());
    if (message.type() === "warning") browserSignals.consoleWarnings.push(message.text());
  });
  page.on("pageerror", (error) => browserSignals.pageErrors.push(error.message));
  const cdp = await context.newCDPSession(page);
  await cdp.send("Network.enable");
  await cdp.send("Performance.enable");
  await cdp.send("Emulation.setCPUThrottlingRate", { rate: cpuRate });
  let maxLayers = 0;
  try {
    await cdp.send("LayerTree.enable");
    cdp.on("LayerTree.layerTreeDidChange", (event) => {
      maxLayers = Math.max(maxLayers, event.layers?.length || 0);
    });
  } catch {
    // LayerTree is not available in every Chromium mode.
  }
  const network = createNetworkTracker(cdp);

  const load = async (label) => {
    network.reset();
    const before = metricMap((await cdp.send("Performance.getMetrics")).metrics);
    if (label === "cold") await page.goto(url, { waitUntil: "domcontentloaded", timeout: 60000 });
    else await page.reload({ waitUntil: "domcontentloaded", timeout: 60000 });
    await waitForSurface(page, url.includes("#/archive") ? "archive" : "today");
    await page.waitForTimeout(settleMs);
    const interaction = await applyAction(page, action);
    if (interaction) await page.waitForTimeout(300);
    const frameSample = await sampleFrames(page, fpsSampleMs);
    const after = metricMap((await cdp.send("Performance.getMetrics")).metrics);
    const snapshot = await pageSnapshot(page);
    return {
      name: `${name}-${label}`,
      url,
      viewport,
      reducedMotion,
      cpuRate,
      cacheState: label,
      interaction,
      frameSample,
      layers: { max: maxLayers },
      cdp: {
        taskDurationMs: ((after.TaskDuration || 0) - (before.TaskDuration || 0)) * 1000,
        scriptDurationMs: ((after.ScriptDuration || 0) - (before.ScriptDuration || 0)) * 1000,
        layoutDurationMs: ((after.LayoutDuration || 0) - (before.LayoutDuration || 0)) * 1000,
        recalcStyleDurationMs: ((after.RecalcStyleDuration || 0) - (before.RecalcStyleDuration || 0)) * 1000,
        layoutCount: (after.LayoutCount || 0) - (before.LayoutCount || 0),
        recalcStyleCount: (after.RecalcStyleCount || 0) - (before.RecalcStyleCount || 0),
        jsHeapUsedBytes: after.JSHeapUsedSize || 0,
        jsHeapTotalBytes: after.JSHeapTotalSize || 0
      },
      network: network.snapshot(),
      browserSignals,
      page: snapshot
    };
  };

  const results = [await load("cold")];
  if (warm) results.push(await load("warm"));
  await context.close();
  return results;
}

async function main() {
  await mkdir(outputDir, { recursive: true });
  const browser = await chromium.launch({ headless: true, channel: browserChannel });
  const scenarios = [];
  try {
    if (shouldRun("today-desktop")) {
      scenarios.push(
        ...(await measurePage({
          browser,
          name: "today-desktop",
          url: todayUrl,
          viewport: { width: 1280, height: 720 },
          warm: true
        }))
      );
    }
    if (shouldRun("today-mobile")) {
      scenarios.push(
        ...(await measurePage({
          browser,
          name: "today-mobile",
          url: todayUrl,
          viewport: { width: 375, height: 812 },
          warm: true
        }))
      );
    }
    for (const scenario of [
      { name: "today-reduced-motion", url: todayUrl, reducedMotion: "reduce" },
      { name: "archive-desktop", url: archiveUrl },
      { name: "viewer-desktop", url: todayUrl, action: "viewer" },
      { name: "ambient-desktop", url: todayUrl, action: "ambient" },
      { name: "share-desktop", url: todayUrl, action: "share" }
    ]) {
      if (!shouldRun(scenario.name)) continue;
      scenarios.push(
        ...(await measurePage({
          browser,
          viewport: { width: 1280, height: 720 },
          ...scenario
        }))
      );
    }
  } finally {
    await browser.close();
  }

  if (shouldRun("today-disable-gpu")) {
    const gpuOffBrowser = await chromium.launch({
      headless: true,
      channel: browserChannel,
      args: ["--disable-gpu"]
    });
    try {
      scenarios.push(
        ...(await measurePage({
          browser: gpuOffBrowser,
          name: "today-disable-gpu",
          url: todayUrl,
          viewport: { width: 1280, height: 720 }
        }))
      );
    } finally {
      await gpuOffBrowser.close();
    }
  }

  const payload = {
    meta: {
      generatedAt: new Date().toISOString(),
      baseUrl,
      auditDate,
      cpuRate,
      settleMs,
      fpsSampleMs,
      browserChannel,
      chromium: chromium.name(),
      requestedScenarios: [...requestedScenarios],
      note: "Synthetic Playwright/CDP baseline; compare repeated runs on the same machine and browser."
    },
    scenarios
  };
  const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
  const timestamped = path.join(outputDir, `baseline-${timestamp}.json`);
  const latest = path.join(outputDir, "latest.json");
  const text = `${JSON.stringify(payload, null, 2)}\n`;
  await writeFile(timestamped, text, "utf8");
  await writeFile(latest, text, "utf8");
  console.log(`performance_baseline=${timestamped}`);
  console.log(`performance_latest=${latest}`);
  console.log(`scenarios=${scenarios.length}`);
}

await main();
