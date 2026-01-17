import { Marquee } from "./Marquee";

interface HudProps {
  batchId: string;
  status: "OK" | "DEGRADED" | "ERROR";
  marqueeItems: string[];
}

const statusStyles: Record<HudProps["status"], string> = {
  OK: "text-acid-green border-acid-green/60",
  DEGRADED: "text-yellow-300 border-yellow-300/60",
  ERROR: "text-alert-red border-alert-red/60"
};

export function Hud({ batchId, status, marqueeItems }: HudProps) {
  return (
    <header className="hud-border sticky top-0 z-20 bg-panel-900/90 backdrop-blur-lg">
      <div className="flex flex-wrap items-center gap-4 px-4 py-3 md:px-6">
        <div className="flex flex-col">
          <span className="text-[10px] uppercase tracking-[0.4em] text-clinical-white/50">Batch ID</span>
          <span className="font-mono text-sm tracking-[0.2em]">{batchId}</span>
        </div>
        <div className="ml-auto flex items-center gap-3">
          <span className="text-[10px] uppercase tracking-[0.4em] text-clinical-white/50">Status</span>
          <span
            className={`rounded-full border px-3 py-1 text-xs font-semibold uppercase ${statusStyles[status]}`}
          >
            {status}
          </span>
        </div>
      </div>
      <div className="border-t border-panel-700/70 px-4 py-2 md:px-6">
        <Marquee items={marqueeItems} />
      </div>
    </header>
  );
}
