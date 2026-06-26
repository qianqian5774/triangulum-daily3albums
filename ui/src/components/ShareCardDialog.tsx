import { useEffect, useMemo, useRef, useState } from "react";
import { flushSync } from "react-dom";
import type { Language } from "../strings/copy";
import type { VisualTheme } from "../lib/bjt";
import type { PickItem, TodayIssue } from "../lib/types";
import { resolveCoverUrl } from "../lib/covers";
import { useT, useUiSettings } from "../lib/ui-settings";
import {
  createShareCardFileName,
  downloadShareCardPng,
  getAvailableShareVersions,
  getDefaultShareVersionId,
  getShareCardAlbumCount,
  getShareCardSlots,
  getShareCardVersion,
  type ShareCardSlot,
  type ShareCardTheme,
  type ShareCardVersionId
} from "../lib/share-card";

interface ShareCardDialogProps {
  open: boolean;
  issue: TodayIssue | null;
  nowSlotId: number | null;
  visualTheme: VisualTheme;
  onClose: () => void;
}

interface ShareCardCopy {
  brand: string;
  date: string;
  bjt: string;
  daily: string;
  window: string;
  noCover: string;
  footer: [string, string, string];
  versionSuffix: string;
}

const shareCopy: Record<Language, ShareCardCopy> = {
  en: {
    brand: "TRIANGULUM DAILY 3 ALBUMS",
    date: "DATE",
    bjt: "BJT",
    daily: "UNLOCKED ALBUMS",
    window: "WINDOW",
    noCover: "NO COVER",
    footer: ["ANTI-FEED", "ALBUMS ONLY", "STATIC SIGNAL"],
    versionSuffix: "ALBUMS UNLOCKED"
  },
  zh: {
    brand: "TRIANGULUM\n每日专辑信号",
    date: "日期",
    bjt: "北京时间",
    daily: "已解锁专辑",
    window: "时段",
    noCover: "无封面",
    footer: ["反信息流", "只按专辑听", "静态信号"],
    versionSuffix: "张已解锁"
  }
};

const slotTimes = ["06:00", "12:00", "18:00"];

function truncateMeta(value: string, fallback: string) {
  const trimmed = value.trim();
  return trimmed || fallback;
}

function ShareCardCover({
  issue,
  pick,
  language
}: {
  issue: TodayIssue;
  pick: PickItem | null;
  language: Language;
}) {
  const copy = shareCopy[language];
  const [coverFailed, setCoverFailed] = useState(false);
  const coverUrl = pick
    ? resolveCoverUrl(pick.cover.optimized_cover_url, pick.cover.cover_version ?? issue.run_id ?? issue.date)
    : null;
  return (
    <article className="share-card-pick">
      <div className="share-card-cover">
        {coverUrl && pick?.cover.has_cover && !coverFailed ? (
          <img src={coverUrl} alt="" crossOrigin="anonymous" onError={() => setCoverFailed(true)} />
        ) : (
          <div className="share-card-no-cover">{copy.noCover}</div>
        )}
      </div>
      <div className="share-card-pick-meta">
        <p className="share-card-pick-title">
          {pick ? truncateMeta(pick.title, String(copy.noCover)) : String(copy.noCover)}
        </p>
        <p className="share-card-pick-artist">
          {pick ? truncateMeta(pick.artist_credit, "UNKNOWN ARTIST") : "SIGNAL EMPTY"}
        </p>
      </div>
    </article>
  );
}

function ShareCardSection({
  issue,
  slot,
  index,
  language
}: {
  issue: TodayIssue;
  slot: ShareCardSlot;
  index: number;
  language: Language;
}) {
  const copy = shareCopy[language];
  const paddedPicks: Array<PickItem | null> = [...slot.picks.slice(0, 3)];
  while (paddedPicks.length < 3) {
    paddedPicks.push(null);
  }
  return (
    <section className="share-card-window">
      <div className="share-card-window-label">
        <span>{slotTimes[slot.slotId] ?? slot.windowLabel}</span>
        <small>
          {copy.window} {String(index + 1).padStart(2, "0")} / {copy.bjt}
        </small>
      </div>
      <div className="share-card-picks">
        {paddedPicks.map((pick, pickIndex) => (
          <ShareCardCover
            // eslint-disable-next-line react/no-array-index-key
            key={`${slot.slotId}-${pickIndex}`}
            issue={issue}
            pick={pick}
            language={language}
          />
        ))}
      </div>
    </section>
  );
}

export function ShareCardCanvas({
  issue,
  slots,
  versionId,
  theme,
  language
}: {
  issue: TodayIssue;
  slots: ShareCardSlot[];
  versionId: ShareCardVersionId;
  theme: ShareCardTheme;
  language: Language;
}) {
  const copy = shareCopy[language];
  const version = getShareCardVersion(versionId);
  const albumCount = getShareCardAlbumCount(issue, versionId);
  const footer = copy.footer;

  return (
    <div
      className="share-card-canvas"
      data-share-theme={theme}
      data-share-count={slots.length}
      data-testid="share-card-canvas"
    >
      <div className="share-card-texture" aria-hidden="true" />
      <header className="share-card-header">
        <div>
          <p className="share-card-kicker">{copy.daily}</p>
          <h2>{copy.brand}</h2>
        </div>
        <div className="share-card-datebox">
          <span>{copy.date}</span>
          <strong>{issue.date}</strong>
          <span>{copy.bjt}</span>
          <strong>
            {language === "zh" ? `${albumCount}${copy.versionSuffix}` : `${albumCount} ${copy.versionSuffix}`}
          </strong>
        </div>
      </header>
      <main className="share-card-windows">
        {slots.map((slot, index) => (
          <ShareCardSection key={slot.slotId} issue={issue} slot={slot} index={index} language={language} />
        ))}
      </main>
      <footer className="share-card-footer">
        <span>{footer[0]}</span>
        <span>{footer[1]}</span>
        <span>{footer[2]}</span>
        <small>
          {version.windowLabel} / {version.albumCount}
        </small>
      </footer>
    </div>
  );
}

export function ShareCardDialog({ open, issue, nowSlotId, visualTheme, onClose }: ShareCardDialogProps) {
  const tx = useT();
  const { language: uiLanguage } = useUiSettings();
  const exportRef = useRef<HTMLDivElement | null>(null);
  const [theme, setTheme] = useState<ShareCardTheme>(visualTheme);
  const [language, setLanguage] = useState<Language>(uiLanguage);
  const [versionId, setVersionId] = useState<ShareCardVersionId>(() => getDefaultShareVersionId(nowSlotId));
  const [isExporting, setIsExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  const availableVersions = useMemo(() => getAvailableShareVersions(nowSlotId), [nowSlotId]);
  const availableVersionIds = useMemo(() => new Set(availableVersions.map((version) => version.id)), [availableVersions]);

  useEffect(() => {
    if (!open) {
      return;
    }
    setTheme(visualTheme);
    setLanguage(uiLanguage);
    setVersionId(getDefaultShareVersionId(nowSlotId));
    setExportError(null);
  }, [nowSlotId, open, uiLanguage, visualTheme]);

  useEffect(() => {
    if (!availableVersionIds.has(versionId)) {
      setVersionId(getDefaultShareVersionId(nowSlotId));
    }
  }, [availableVersionIds, nowSlotId, versionId]);

  const slots = useMemo(() => (issue ? getShareCardSlots(issue, versionId) : []), [issue, versionId]);
  const canExport = Boolean(issue && availableVersionIds.has(versionId) && slots.length);

  if (!open) {
    return null;
  }

  const handleDownload = async () => {
    if (!issue || !canExport) {
      return;
    }
    flushSync(() => {
      setIsExporting(true);
      setExportError(null);
    });
    try {
      if (!exportRef.current) {
        throw new Error("Share card export root is unavailable");
      }
      await downloadShareCardPng(exportRef.current, createShareCardFileName(issue, versionId, theme, language));
    } catch (err) {
      setExportError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="share-dialog-backdrop" role="presentation">
      <div className="share-dialog" role="dialog" aria-modal="true" aria-label={tx("share.title")}>
        <div className="share-dialog-panel">
          <div className="share-dialog-heading">
            <div>
              <p className="ui-kicker text-clinical-white/50">{tx("share.eyebrow")}</p>
              <h2>{tx("share.title")}</h2>
              <p>{tx("share.description")}</p>
            </div>
            <button type="button" className="ui-button" onClick={onClose}>
              {tx("share.close")}
            </button>
          </div>

          <div className="share-controls">
            <div>
              <p>{tx("share.version")}</p>
              <div className="share-control-row">
                {(["0600", "1200", "1800"] as ShareCardVersionId[]).map((id) => {
                  const version = getShareCardVersion(id);
                  const enabled = availableVersionIds.has(id);
                  return (
                    <button
                      key={id}
                      type="button"
                      disabled={!enabled}
                      data-testid={`share-version-${id}`}
                      className={versionId === id ? "is-active" : ""}
                      onClick={() => setVersionId(id)}
                    >
                      {version.windowLabel} · {version.albumCount}
                    </button>
                  );
                })}
              </div>
            </div>

            <div>
              <p>{tx("share.theme")}</p>
              <div className="share-control-row">
                <button
                  type="button"
                  data-testid="share-theme-day"
                  className={theme === "day" ? "is-active" : ""}
                  onClick={() => setTheme("day")}
                >
                  {tx("share.day")}
                </button>
                <button
                  type="button"
                  data-testid="share-theme-night"
                  className={theme === "night" ? "is-active" : ""}
                  onClick={() => setTheme("night")}
                >
                  {tx("share.night")}
                </button>
              </div>
            </div>

            <div>
              <p>{tx("share.language")}</p>
              <div className="share-control-row">
                <button
                  type="button"
                  data-testid="share-language-en"
                  className={language === "en" ? "is-active" : ""}
                  onClick={() => setLanguage("en")}
                >
                  EN
                </button>
                <button
                  type="button"
                  data-testid="share-language-zh"
                  className={language === "zh" ? "is-active" : ""}
                  onClick={() => setLanguage("zh")}
                >
                  中文
                </button>
              </div>
            </div>
          </div>

          {!canExport ? <div className="share-warning">{tx("share.locked")}</div> : null}
          {exportError ? <div className="share-warning">{exportError}</div> : null}

          <div className="share-actions">
            <button type="button" className="ui-button" disabled={!canExport || isExporting} onClick={handleDownload}>
              {isExporting ? tx("share.exporting") : tx("share.download")}
            </button>
          </div>
        </div>

        <div className="share-preview-panel">
          {issue && slots.length ? (
            <div className="share-card-preview-frame">
              <ShareCardCanvas
                issue={issue}
                slots={slots}
                versionId={versionId}
                theme={theme}
                language={language}
              />
            </div>
          ) : null}
        </div>

        {issue && slots.length ? (
          <div className={`share-card-export-root ${isExporting ? "is-exporting" : ""}`} aria-hidden="true">
            <div ref={exportRef}>
              <ShareCardCanvas
                issue={issue}
                slots={slots}
                versionId={versionId}
                theme={theme}
                language={language}
              />
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
