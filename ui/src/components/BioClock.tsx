import { useEffect, useMemo, useState } from "react";
import { cn } from "../lib/cn";
import { t } from "../strings/t";

interface BioClockProps {
  nextRefreshAt?: string | null;
  className?: string;
}

const TICK_MS = 50;

function resolveTarget(nextRefreshAt?: string | null): Date {
  if (nextRefreshAt) {
    const parsed = new Date(nextRefreshAt);
    if (!Number.isNaN(parsed.getTime())) {
      return parsed;
    }
  }
  const now = new Date();
  const target = new Date(now);
  target.setHours(24, 0, 0, 0);
  return target;
}

function formatCountdown(diffMs: number) {
  const safe = Math.max(0, diffMs);
  const centiseconds = Math.floor(safe / 10) % 100;
  const totalSeconds = Math.floor(safe / 1000);
  const seconds = totalSeconds % 60;
  const totalMinutes = Math.floor(totalSeconds / 60);
  const minutes = totalMinutes % 60;
  const hours = Math.floor(totalMinutes / 60);
  return { hours, minutes, seconds, centiseconds };
}

function pad2(value: number) {
  return value.toString().padStart(2, "0");
}

export function BioClock({ nextRefreshAt, className }: BioClockProps) {
  const target = useMemo(() => resolveTarget(nextRefreshAt), [nextRefreshAt]);
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    const timer = window.setInterval(() => {
      setNow(Date.now());
    }, TICK_MS);
    return () => window.clearInterval(timer);
  }, []);

  const { hours, minutes, seconds, centiseconds } = useMemo(
    () => formatCountdown(target.getTime() - now),
    [now, target]
  );

  return (
    <div className={cn("flex flex-col items-end gap-1 text-right", className)}>
      <span className="text-[10px] uppercase tracking-[0.4em] text-clinical-white/50">
        {t("hud.clock.nextCycle")}
      </span>
      <span className="font-mono text-xs uppercase tracking-[0.25em] text-acid-green respire">
        {t("hud.clock.tMinus")} {pad2(hours)}
        <span className="pulse-separator">:</span>
        {pad2(minutes)}
        <span className="pulse-separator">:</span>
        {pad2(seconds)}
        <span className="pulse-separator">:</span>
        {pad2(centiseconds)}
      </span>
    </div>
  );
}
