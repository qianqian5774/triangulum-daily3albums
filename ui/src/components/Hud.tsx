import { useEffect, useMemo, useRef } from "react";
import { Link, useLocation } from "react-router-dom";
import { Marquee } from "./Marquee";
import { useT, useUiSettings } from "../lib/ui-settings";

interface HudProps {
  status: "OK" | "DEGRADED" | "ERROR" | "OFFLINE" | "ARCHIVE";
  marqueeItems: string[];
  bjtTime: string;
  windowLabel: string;
  nextUnlockLabel: string;
  countdownLabel: string;
  statusMessage?: string | null;
  debugActive?: boolean;
  onOpenAbout: () => void;
}

const statusStyles: Record<HudProps["status"], string> = {
  OK: "text-signal-accent border-signal-accent/60",
  DEGRADED: "text-yellow-300 border-yellow-300/60",
  ERROR: "text-alert-red border-alert-red/60",
  OFFLINE: "text-alert-red border-alert-red/60",
  ARCHIVE: "text-yellow-300 border-yellow-300/60"
};

export function Hud({
  status,
  marqueeItems,
  bjtTime,
  windowLabel,
  nextUnlockLabel,
  countdownLabel,
  statusMessage,
  debugActive,
  onOpenAbout
}: HudProps) {
  const tx = useT();
  const { language, setLanguage, decreaseFont, increaseFont, resetFont } = useUiSettings();
  const location = useLocation();
  const headerRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!headerRef.current || typeof ResizeObserver === "undefined") {
      return;
    }
    const updateHeight = () => {
      if (!headerRef.current) {
        return;
      }
      document.documentElement.style.setProperty("--hud-height", `${Math.ceil(headerRef.current.offsetHeight)}px`);
    };
    updateHeight();
    const observer = new ResizeObserver(updateHeight);
    observer.observe(headerRef.current);
    return () => {
      observer.disconnect();
      document.documentElement.style.removeProperty("--hud-height");
    };
  }, []);

  const statusLabels = useMemo<Record<HudProps["status"], string>>(
    () => ({
      OK: tx("system.status.operational"),
      DEGRADED: tx("system.status.degraded"),
      ERROR: tx("system.status.error"),
      OFFLINE: tx("system.status.offline"),
      ARCHIVE: tx("system.status.archiveMode")
    }),
    [tx]
  );

  const isArchive = location.pathname.startsWith("/archive");

  return (
    <header
      ref={headerRef}
      className="hud-shell hud-border fixed z-[60] rounded-card bg-panel-900/94 backdrop-blur-lg"
    >
      <div className="hud-grid px-3 py-3 md:px-4">
        <div className="hud-time">
          <span className="hud-clock-line text-clinical-white/50">{tx("hud.labels.bjt")}</span>
          <span className="hud-clock-line font-mono respire">
            {bjtTime}
          </span>
          <span className="hud-clock-line text-clinical-white/60">{windowLabel}</span>
          <span className="hud-clock-line font-semibold text-signal-accent">
            {nextUnlockLabel}
          </span>
          <span className="hud-clock-line font-mono text-signal-accent/80">
            {countdownLabel}
          </span>
        </div>

        <div className="hud-status">
          <div className="flex flex-wrap items-center justify-center gap-2">
            <span className="ui-kicker text-clinical-white/50">{tx("hud.labels.status")}</span>
            <span
              className={`rounded-full border px-3 py-1 text-[0.68rem] font-semibold uppercase tracking-[0.22em] ${
                statusStyles[status]
              }`}
            >
              {statusLabels[status]}
            </span>
          </div>
          {debugActive ? (
            <span className="rounded-full border border-alert-red/60 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.3em] text-alert-red">
              {tx("hud.labels.debug")}
            </span>
          ) : null}
        </div>

        <nav className="hud-actions" aria-label="Primary">
          <Link
            to="/"
            className={`ui-button ${isArchive ? "border-panel-700/80 text-clinical-white/70" : "border-signal-accent/70 text-signal-accent"}`}
          >
            {tx("nav.today")}
          </Link>
          <Link
            to="/archive"
            className={`ui-button ${isArchive ? "border-signal-accent/70 text-signal-accent" : "border-panel-700/80 text-clinical-white/70"}`}
          >
            {tx("nav.archive")}
          </Link>
          <button type="button" onClick={onOpenAbout} className="ui-button border-panel-700/80 text-clinical-white/70">
            {tx("nav.about")}
          </button>
        </nav>

        <div className="hud-settings" aria-label="Display settings">
          <div className="segmented-control hud-language-control" aria-label={tx("controls.language")}>
            <button
              type="button"
              onClick={() => setLanguage("en")}
              className={language === "en" ? "is-active" : ""}
            >
              {tx("controls.english")}
            </button>
            <button
              type="button"
              onClick={() => setLanguage("zh")}
              className={language === "zh" ? "is-active" : ""}
            >
              {tx("controls.chinese")}
            </button>
          </div>
          <div className="segmented-control hud-font-control" aria-label={tx("controls.font")}>
            <button type="button" onClick={decreaseFont} aria-label={tx("controls.fontDown")}>
              {tx("controls.fontDown")}
            </button>
            <button type="button" onClick={increaseFont} aria-label={tx("controls.fontUp")}>
              {tx("controls.fontUp")}
            </button>
            <button type="button" onClick={resetFont} aria-label={tx("controls.fontReset")}>
              {tx("controls.fontReset")}
            </button>
          </div>
        </div>
      </div>
      {statusMessage ? (
        <div className="border-t border-panel-700/70 px-4 py-2 text-[0.72rem] uppercase tracking-[0.18em] text-clinical-white/60 md:px-6">
          {statusMessage}
        </div>
      ) : null}
      <div className="hud-marquee border-t border-panel-700/70 px-4 py-3 md:px-6">
        <Marquee items={marqueeItems} />
      </div>
    </header>
  );
}
