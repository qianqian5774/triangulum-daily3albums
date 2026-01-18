import { Link, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { FLAGS } from "../config/flags";
import { BioClock } from "./BioClock";
import { Marquee } from "./Marquee";

interface HudProps {
  batchId: string;
  status: "OK" | "DEGRADED" | "ERROR";
  marqueeItems: string[];
  scale: number;
  onScaleChange: (next: number) => void;
}

const statusStyles: Record<HudProps["status"], string> = {
  OK: "text-acid-green border-acid-green/60",
  DEGRADED: "text-yellow-300 border-yellow-300/60",
  ERROR: "text-alert-red border-alert-red/60"
};

const scaleSteps = [0.9, 1, 1.1, 1.2];

const statusLabels: Record<HudProps["status"], string> = {
  OK: "system.status.operational",
  DEGRADED: "system.status.degraded",
  ERROR: "system.status.error"
};

function LanguageToggle({ value, onToggle }: { value: string; onToggle: () => void }) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className="rounded-hud border border-acid-green/40 px-3 py-2 font-mono text-[10px] uppercase tracking-[0.3em] text-acid-green/90 transition hover:border-acid-green/70"
    >
      {value.toUpperCase()}
    </button>
  );
}

export function Hud({ batchId, status, marqueeItems, scale, onScaleChange }: HudProps) {
  const { t, i18n } = useTranslation();
  const location = useLocation();

  const cycleScale = () => {
    const currentIndex = scaleSteps.findIndex((step) => Math.abs(step - scale) < 0.01);
    const nextIndex = (currentIndex + 1) % scaleSteps.length;
    onScaleChange(scaleSteps[nextIndex]);
  };

  return (
    <header className="hud-border sticky top-0 z-20 bg-panel-900/90 backdrop-blur-lg">
      <div className="flex flex-wrap items-center gap-4 px-4 py-3 md:px-6">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-6">
          <div className="flex flex-col">
            <span className="text-[10px] uppercase tracking-[0.4em] text-clinical-white/50">
              {t("system.batch.label")}
            </span>
            <span className="font-mono text-sm tracking-[0.2em]">{batchId}</span>
          </div>
          <nav className="flex items-center gap-3 text-xs uppercase tracking-[0.3em] text-clinical-white/60">
            <Link
              to="/"
              className={`rounded-hud border px-3 py-1 transition ${
                location.pathname === "/"
                  ? "border-acid-green/70 text-acid-green"
                  : "border-panel-700/60 hover:border-clinical-white/40"
              }`}
            >
              {t("navigation.today")}
            </Link>
            <Link
              to="/archive"
              className={`rounded-hud border px-3 py-1 transition ${
                location.pathname === "/archive"
                  ? "border-acid-green/70 text-acid-green"
                  : "border-panel-700/60 hover:border-clinical-white/40"
              }`}
            >
              {t("navigation.archive")}
            </Link>
          </nav>
        </div>
        <div className="ml-auto flex flex-wrap items-center gap-4">
          {FLAGS.bioClock && (
            <div className="breath">
              <BioClock />
            </div>
          )}
          {FLAGS.scaleControl && (
            <button
              type="button"
              onClick={cycleScale}
              className="rounded-hud border border-panel-700/70 px-3 py-2 font-mono text-[10px] uppercase tracking-[0.3em] text-clinical-white/60 transition hover:border-clinical-white/50"
            >
              {t("hud.scale")} {Math.round(scale * 100)}%
            </button>
          )}
          {FLAGS.i18n && (
            <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.3em] text-clinical-white/50">
              <span>{t("hud.language")}</span>
              <LanguageToggle
                value={i18n.language}
                onToggle={() => i18n.changeLanguage(i18n.language === "en" ? "zh" : "en")}
              />
            </div>
          )}
          <div className="flex items-center gap-3">
            <span className="text-[10px] uppercase tracking-[0.4em] text-clinical-white/50">
              {t("system.status.label")}
            </span>
            <span
              className={`rounded-full border px-3 py-1 text-xs font-semibold uppercase ${statusStyles[status]}`}
            >
              {t(statusLabels[status])}
            </span>
          </div>
        </div>
      </div>
      <div className="border-t border-panel-700/70 px-4 py-2 md:px-6">
        <Marquee items={marqueeItems} />
      </div>
    </header>
  );
}
