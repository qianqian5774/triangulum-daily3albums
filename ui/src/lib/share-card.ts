import type { Language } from "../strings/copy";
import type { PickItem, TodayIssue, TodaySlot } from "./types";

export type ShareCardTheme = "day" | "night";
export type ShareCardVersionId = "0600" | "1200" | "1800";

export interface ShareCardVersion {
  id: ShareCardVersionId;
  maxSlotId: number;
  albumCount: number;
  windowLabel: string;
}

export interface ShareCardSlot {
  slotId: number;
  windowLabel: string;
  theme: string;
  picks: PickItem[];
}

export const SHARE_CARD_VERSIONS: ShareCardVersion[] = [
  { id: "0600", maxSlotId: 0, albumCount: 3, windowLabel: "06:00" },
  { id: "1200", maxSlotId: 1, albumCount: 6, windowLabel: "12:00" },
  { id: "1800", maxSlotId: 2, albumCount: 9, windowLabel: "18:00" }
];

function normalizeSlots(issue: TodayIssue): TodaySlot[] {
  if (issue.slots?.length) {
    return [...issue.slots].sort((a, b) => a.slot_id - b.slot_id);
  }
  return [
    {
      slot_id: issue.now_slot_id ?? 0,
      window_label: "06:00-11:59",
      theme: issue.theme_of_day,
      picks: issue.picks
    }
  ];
}

export function getAvailableShareVersions(nowSlotId: number | null | undefined) {
  if (nowSlotId === null || nowSlotId === undefined || nowSlotId < 0) {
    return [] as ShareCardVersion[];
  }
  return SHARE_CARD_VERSIONS.filter((version) => version.maxSlotId <= nowSlotId);
}

export function getDefaultShareVersionId(nowSlotId: number | null | undefined): ShareCardVersionId {
  const versions = getAvailableShareVersions(nowSlotId);
  return versions[versions.length - 1]?.id ?? "0600";
}

export function getShareCardVersion(id: ShareCardVersionId) {
  return SHARE_CARD_VERSIONS.find((version) => version.id === id) ?? SHARE_CARD_VERSIONS[0];
}

export function getShareCardSlots(issue: TodayIssue, versionId: ShareCardVersionId): ShareCardSlot[] {
  const version = getShareCardVersion(versionId);
  return normalizeSlots(issue)
    .filter((slot) => slot.slot_id <= version.maxSlotId)
    .slice(0, version.maxSlotId + 1)
    .map((slot) => ({
      slotId: slot.slot_id,
      windowLabel: slot.window_label,
      theme: slot.theme,
      picks: slot.picks.slice(0, 3)
    }));
}

export function getShareCardAlbumCount(issue: TodayIssue, versionId: ShareCardVersionId) {
  return getShareCardSlots(issue, versionId).reduce((total, slot) => total + slot.picks.length, 0);
}

export function createShareCardFileName(
  issue: TodayIssue,
  versionId: ShareCardVersionId,
  theme: ShareCardTheme,
  language: Language
) {
  return `triangulum-${issue.date}-${versionId}-${theme}-${language}.png`;
}

export async function waitForShareCardImages(root: HTMLElement, timeoutMs = 9000) {
  const images = Array.from(root.querySelectorAll("img"));
  if (!images.length) {
    return;
  }
  await Promise.race([
    Promise.all(
      images.map((image) => {
        if (image.complete && image.naturalWidth > 0) {
          return Promise.resolve();
        }
        return new Promise<void>((resolve) => {
          const finish = () => resolve();
          image.addEventListener("load", finish, { once: true });
          image.addEventListener("error", finish, { once: true });
          if (image.decode) {
            image.decode().then(finish).catch(finish);
          }
        });
      })
    ),
    new Promise<void>((resolve) => {
      window.setTimeout(resolve, timeoutMs);
    })
  ]);
}

export async function downloadShareCardPng(root: HTMLElement, filename: string) {
  await waitForShareCardImages(root);
  const html2canvas = (await import("html2canvas")).default;
  const canvas = await html2canvas(root, {
    backgroundColor: null,
    scale: 1,
    useCORS: true,
    allowTaint: false,
    logging: false,
    width: 1080,
    height: 1440,
    windowWidth: 1080,
    windowHeight: 1440
  });
  const blob = await new Promise<Blob>((resolve, reject) => {
    canvas.toBlob((nextBlob) => {
      if (nextBlob) {
        resolve(nextBlob);
      } else {
        reject(new Error("Share card PNG export failed"));
      }
    }, "image/png");
  });
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
}
