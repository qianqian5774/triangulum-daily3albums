import { Marquee } from "./Marquee";
import { t } from "../strings/t";

interface HudProps {
  status: "OK" | "DEGRADED" | "ERROR";
  marqueeItems: string[];
  bjtTime: string;
  windowLabel: string;
  nextUnlockLabel: string;
  countdownLabel: string;
  statusMessage?: string | null;
  debugActive?: boolean;
  lastSuccess?: string | null;
}

const statusStyles: Record<HudProps["status"], string> = {
  OK: "text-acid-green border-acid-green/60",
  DEGRADED: "text-yellow-300 border-yellow-300/60",
  ERROR: "text-alert-red border-alert-red/60"
};

const statusLabels: Record<HudProps["status"], string> = {
  OK: t("system.status.operational"),
  DEGRADED: t("system.status.degraded"),
  ERROR: t("system.status.error")
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
  lastSuccess
}: HudProps) {
  return (
    <header className="hud-border sticky top-0 z-20 bg-panel-900/90 backdrop-blur-lg">
      <div className="flex flex-wrap items-center gap-4 px-4 py-3 md:px-6">
        <div className="flex flex-col gap-1">
          <span className="text-[10px] uppercase tracking-[0.4em] text-clinical-white/50">{t("hud.labels.bjt")}</span>
          <span className="font-mono text-2xl tracking-[0.35em] respire">{bjtTime}</span>
          <span className="text-[11px] uppercase tracking-[0.3em] text-clinical-white/60">{windowLabel}</span>
          <span className="text-sm font-semibold uppercase tracking-[0.3em] text-acid-green">
            {nextUnlockLabel}
          </span>
          <span className="font-mono text-xs uppercase tracking-[0.25em] text-acid-green/80">
            {countdownLabel}
          </span>
          {lastSuccess ? (
            <span className="text-[10px] uppercase tracking-[0.25em] text-clinical-white/40">
              {t("hud.labels.lastSuccess")} {lastSuccess}
            </span>
          ) : null}
        </div>
        <div className="ml-auto flex flex-wrap items-center gap-6">
          <div className="flex items-center gap-3">
            <span className="text-[10px] uppercase tracking-[0.4em] text-clinical-white/50">
              {t("hud.labels.status")}
            </span>
            <span
              className={`rounded-full border px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.3em] ${
                statusStyles[status]
              }`}
            >
              {statusLabels[status]}
            </span>
          </div>
          {debugActive ? (
            <span className="rounded-full border border-alert-red/60 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.3em] text-alert-red">
              {t("hud.labels.debug")}
            </span>
          ) : null}
        </div>
      </div>
      {statusMessage ? (
        <div className="border-t border-panel-700/70 px-4 py-2 text-[11px] uppercase tracking-[0.25em] text-clinical-white/60 md:px-6">
          {statusMessage}
        </div>
      ) : null}
      <div className="border-t border-panel-700/70 px-4 py-2 md:px-6">
        <Marquee items={marqueeItems} />
      </div>
    </header>
  );
}
