import { BioClock } from "./BioClock";
import { Marquee } from "./Marquee";
import { FLAGS } from "../config/flags";
import { t } from "../strings/t";

interface HudProps {
  batchId: string;
  status: "OK" | "DEGRADED" | "ERROR";
  marqueeItems: string[];
  nextRefreshAt?: string | null;
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

export function Hud({ batchId, status, marqueeItems, nextRefreshAt }: HudProps) {
  return (
    <header className="hud-border sticky top-0 z-20 bg-panel-900/90 backdrop-blur-lg">
      <div className="flex flex-wrap items-center gap-4 px-4 py-3 md:px-6">
        <div className="flex flex-col">
          <span className="text-[10px] uppercase tracking-[0.4em] text-clinical-white/50">
            {t("hud.labels.batchId")}
          </span>
          <span className="font-mono text-sm tracking-[0.2em] respire">{batchId}</span>
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
          {FLAGS.bioClock && <BioClock nextRefreshAt={nextRefreshAt} className="hidden sm:flex" />}
        </div>
      </div>
      {FLAGS.bioClock && (
        <div className="border-t border-panel-700/70 px-4 py-2 md:px-6 sm:hidden">
          <BioClock nextRefreshAt={nextRefreshAt} />
        </div>
      )}
      <div className="border-t border-panel-700/70 px-4 py-2 md:px-6">
        <Marquee items={marqueeItems} />
      </div>
    </header>
  );
}
