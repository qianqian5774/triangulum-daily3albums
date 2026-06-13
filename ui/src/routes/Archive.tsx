import { useContext, useEffect, useMemo, useRef, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { Link } from "react-router-dom";
import { HudContext } from "../App";
import { BSOD } from "../components/BSOD";
import { SlotCard } from "../components/SlotCard";
import { loadArchiveDay, loadArchiveIndex } from "../lib/data";
import { useT } from "../lib/ui-settings";
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
  const tx = useT();
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
          status: "OK",
          marqueeItems: data.picks.map((pick) => `${pick.title} — ${pick.artist_credit}`),
          statusMessage: null,
          lastSuccess: data.run_id ? `${data.date} / ${data.run_id}` : data.date
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
      return tx("archive.selectDate");
    }
    const theme = selectedEntry.theme_of_day;
    const slotSuffix = typeof selectedEntry.slot === "number" ? ` · slot ${selectedEntry.slot + 1}` : "";
    return theme
      ? `${selectedEntry.date}${slotSuffix} · ${tx("today.themePrefix")} ${theme}`
      : `${selectedEntry.date}${slotSuffix}`;
  }, [selectedEntry, tx]);

  if (error) {
    return <BSOD message={`${tx("system.errors.archiveLoad")}: ${error}`} />;
  }

  return (
    <section className="flex flex-col gap-8">
      <div className="section-toolbar flex flex-wrap items-start justify-between gap-4">
        <div className="flex flex-col gap-2">
          <p className="ui-kicker text-clinical-white/60">{tx("archive.label")}</p>
          <h1 className="text-3xl font-semibold uppercase tracking-tightish">{headerText}</h1>
          <p className="font-mono text-sm text-clinical-white/60">{tx("archive.intro")}</p>
        </div>
        <Link
          to="/"
          className="ui-button border-panel-700/80 text-clinical-white/70 hover:border-acid-green/60 hover:text-acid-green"
        >
          {tx("archive.openToday")}
        </Link>
      </div>
      <div className="archive-layout grid gap-8 lg:grid-cols-[minmax(14rem,18rem)_1fr]">
        <div className="hud-border rounded-card bg-panel-900/70 p-4">
          <p className="ui-kicker text-clinical-white/50">{tx("archive.datesLabel")}</p>
          {index ? (
            <motion.ul
              className="archive-date-list mt-4 flex max-h-[420px] flex-col gap-2 overflow-auto pr-2 text-sm"
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
                    className={`w-full rounded-hud border px-3 py-3 text-left font-mono text-[0.76rem] uppercase tracking-[0.22em] transition ${
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
            <p className="mt-4 font-mono text-xs text-clinical-white/50">{tx("archive.loadingIndex")}</p>
          )}
        </div>
        <div>
          {issue ? (
            <div className="album-grid grid gap-6 md:grid-cols-3">
              {issue.picks.map((pick) => (
                <SlotCard key={pick.slot} pick={pick} cacheKey={pick.cover.cover_version ?? coverCacheKey} />
              ))}
            </div>
          ) : (
            <div className="hud-border rounded-card bg-panel-900/60 p-6 font-mono text-sm text-clinical-white/60">
              {tx("archive.empty")}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
