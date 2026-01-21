import { useContext, useEffect, useMemo, useRef, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { HudContext } from "../App";
import { BSOD } from "../components/BSOD";
import { SlotCard } from "../components/SlotCard";
import { loadArchiveDay, loadArchiveIndex } from "../lib/data";
import { t } from "../strings/t";
import type { ArchiveIndex, TodayIssue } from "../lib/types";

const listVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.12 }
  }
};

const itemVariants = {
  hidden: { opacity: 0, x: -12 },
  show: { opacity: 1, x: 0 }
};

export function ArchiveRoute() {
  const hudContext = useContext(HudContext);

  // IMPORTANT:
  // Do NOT put `hudContext` into effects' dependency arrays.
  // `updateHud()` changes HUD state -> Provider value changes -> `hudContext` identity changes
  // -> effects re-run -> fetch again -> infinite loop.
  const updateHudRef = useRef(hudContext?.updateHud);
  useEffect(() => {
    updateHudRef.current = hudContext?.updateHud;
  }, [hudContext?.updateHud]);

  const [index, setIndex] = useState<ArchiveIndex | null>(null);
  const [issue, setIssue] = useState<TodayIssue | null>(null);
  const [selectedEntry, setSelectedEntry] = useState<ArchiveIndex["items"][number] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const prefersReducedMotion = useReducedMotion();
  const coverCacheKey = issue?.run_id ?? issue?.date ?? selectedEntry?.run_id ?? selectedEntry?.date ?? "";

  useEffect(() => {
    let active = true;

    // reset transient errors on (re)mount
    setError(null);

    loadArchiveIndex()
      .then((data) => {
        if (!active) return;
        setIndex(data);

        // Only set the initial date once (avoid pointless state flips).
        setSelectedEntry((prev) => prev ?? data.items[0] ?? null);
      })
      .catch((err: Error) => {
        if (!active) return;
        setError(err.message);
        updateHudRef.current?.({ status: "ERROR" });
      });

    return () => {
      active = false;
    };
  }, []); // ✅ do NOT depend on hudContext

  useEffect(() => {
    if (!selectedEntry) return;

    let active = true;

    // clear old issue while loading a new date (optional, but avoids stale UI)
    setError(null);
    setIssue(null);

    loadArchiveDay(selectedEntry.date, selectedEntry.run_id)
      .then((data) => {
        if (!active) return;
        setIssue(data);
        updateHudRef.current?.({
          batchId: data.run_id ? data.run_id.toUpperCase() : data.date,
          status: "OK",
          marqueeItems: data.picks.map((pick) => `${pick.title} — ${pick.artist_credit}`),
          nextRefreshAt: null
        });
      })
      .catch((err: Error) => {
        if (!active) return;
        setIssue(null);
        setError(err.message);
        updateHudRef.current?.({ status: "ERROR" });
      });

    return () => {
      active = false;
    };
  }, [selectedEntry]); // ✅ do NOT depend on hudContext

  const headerText = useMemo(() => {
    if (!selectedEntry) {
      return t("archive.selectDate");
    }
    const theme = selectedEntry.theme_of_day;
    const slotSuffix = typeof selectedEntry.slot === "number" ? ` · slot ${selectedEntry.slot + 1}` : "";
    return theme
      ? `${selectedEntry.date}${slotSuffix} · ${t("today.themePrefix")} ${theme}`
      : `${selectedEntry.date}${slotSuffix}`;
  }, [selectedEntry]);

  if (error) {
    return <BSOD message={`${t("system.errors.archiveLoad")}: ${error}`} />;
  }

  return (
    <section className="flex flex-col gap-8">
      <div className="flex flex-col gap-2">
        <p className="text-xs uppercase tracking-[0.4em] text-clinical-white/60">{t("archive.label")}</p>
        <h1 className="text-3xl font-semibold uppercase tracking-tightish">{headerText}</h1>
        <p className="font-mono text-sm text-clinical-white/60">{t("archive.intro")}</p>
      </div>
      <div className="grid gap-8 lg:grid-cols-[240px_1fr]">
        <div className="hud-border rounded-card bg-panel-900/70 p-4">
          <p className="text-xs uppercase tracking-[0.4em] text-clinical-white/50">{t("archive.datesLabel")}</p>
          {index ? (
            <motion.ul
              className="mt-4 flex max-h-[340px] flex-col gap-2 overflow-auto pr-2 text-sm"
              variants={prefersReducedMotion ? undefined : listVariants}
              initial={prefersReducedMotion ? undefined : "hidden"}
              animate={prefersReducedMotion ? undefined : "show"}
            >
              {index.items.map((item) => (
                <motion.li
                  key={`${item.date}-${item.run_id ?? "legacy"}`}
                  variants={prefersReducedMotion ? undefined : itemVariants}
                >
                  <button
                    type="button"
                    onClick={() => setSelectedEntry(item)}
                    className={`w-full rounded-hud border px-3 py-2 text-left font-mono text-xs uppercase tracking-[0.3em] transition ${
                      selectedEntry?.date === item.date && selectedEntry?.run_id === item.run_id
                        ? "border-acid-green/70 text-acid-green"
                        : "border-panel-700/70 text-clinical-white/60 hover:border-clinical-white/40"
                    }`}
                  >
                    <span>{item.date}</span>
                    {typeof item.slot === "number" ? (
                      <span className="ml-2 text-[10px] uppercase tracking-[0.2em] text-clinical-white/50">
                        slot {item.slot + 1}
                      </span>
                    ) : null}
                    {item.run_at ? (
                      <span className="ml-2 text-[10px] uppercase tracking-[0.2em] text-clinical-white/40">
                        {item.run_at.slice(11, 19)}
                      </span>
                    ) : null}
                  </button>
                </motion.li>
              ))}
            </motion.ul>
          ) : (
            <p className="mt-4 font-mono text-xs text-clinical-white/50">{t("archive.loadingIndex")}</p>
          )}
        </div>
        <div>
          {issue ? (
            <div className="grid gap-6 md:grid-cols-3">
              {issue.picks.map((pick) => (
                <SlotCard key={pick.slot} pick={pick} cacheKey={pick.cover.cover_version ?? coverCacheKey} />
              ))}
            </div>
          ) : (
            <div className="hud-border rounded-card bg-panel-900/60 p-6 font-mono text-sm text-clinical-white/60">
              {t("archive.empty")}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
