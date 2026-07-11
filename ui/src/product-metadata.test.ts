import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

const indexHtml = readFileSync(new URL("../index.html", import.meta.url), "utf8");
const shareCardSource = readFileSync(
  new URL("./components/ShareCardDialog.tsx", import.meta.url),
  "utf8"
);

describe("Triangulum Daily product metadata", () => {
  it("uses the current product name and nine-album definition", () => {
    expect(indexHtml).toContain("<title>Triangulum Daily — Nine Albums a Day</title>");
    expect(indexHtml).toContain('property="og:title" content="Triangulum Daily"');
    expect(indexHtml).toContain('rel="canonical" href="https://triangulumdaily.space/"');
    expect(indexHtml).toContain("Nine album recommendations every day");
    expect(shareCardSource).toContain('brand: "TRIANGULUM DAILY"');
  });
});
