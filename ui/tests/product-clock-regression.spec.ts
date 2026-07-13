import { expect, test, type Page } from "@playwright/test";

async function buildDate(page: Page) {
  const response = await page.request.get("/data/today.json");
  expect(response.ok()).toBe(true);
  const payload = await response.json();
  expect(typeof payload.date).toBe("string");
  return payload.date as string;
}

test("shared debug clock remains stable across Today, Archive, and Time Lab boundaries", async ({ page }) => {
  const date = await buildDate(page);
  await page.goto(`/#/?debug=1&debug_time=${date}T07:59:59`);

  const hud = page.getByTestId("hud");
  await expect(hud).toContainText("07:59:59");
  await expect(hud).toContainText("DEBUG TIME ACTIVE");
  await expect(page.getByRole("heading", { name: "SYSTEM OFFLINE" })).toBeVisible();

  await page.getByRole("link", { name: "Archive" }).click();
  await expect(page).toHaveURL(/#\/archive/);
  await expect(page.getByRole("heading", { name: "Recent archive" })).toBeVisible();
  await expect(hud).toContainText("07:59:59");
  await expect(hud).toContainText("DEBUG TIME ACTIVE");

  await page.getByRole("link", { name: "Today", exact: true }).click();
  await expect(page).toHaveURL(/#\//);
  await page.getByRole("button", { name: "08:00", exact: true }).click();
  await expect(hud).toContainText("08:00:00");
  await expect(page.getByTestId("album-card-0")).toBeVisible();

  await page.getByRole("button", { name: "12:30", exact: true }).click();
  await expect(hud).toContainText("12:30:00");

  await page.getByRole("button", { name: "16:00", exact: true }).click();
  await expect(hud).toContainText("16:00:00");
  await page.getByTestId("share-card-toggle").click();
  await expect(page.getByRole("dialog", { name: "Share Card" })).toBeVisible();
  await expect(page.getByTestId("share-version-0800")).toBeVisible();
  await expect(page.getByTestId("share-version-1230")).toBeVisible();
  await expect(page.getByTestId("share-version-1600")).toBeVisible();
  await page.getByRole("button", { name: "Close", exact: true }).click();

  await page.getByRole("button", { name: "Clear debug time", exact: true }).click();
  await expect(hud).not.toContainText("DEBUG TIME ACTIVE");
});
