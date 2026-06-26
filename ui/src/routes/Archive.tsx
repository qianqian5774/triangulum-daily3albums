import { useContext, useEffect, useMemo, useRef, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";
import { Link } from "react-router-dom";
import { HudContext } from "../App";
import { BSOD } from "../components/BSOD";
import { SlotCard } from "../components/SlotCard";
import { DEFAULT_ARCHIVE_RETENTION_DAYS, getArchiveIssueSlots, getRecentArchiveEntries } from "../lib/archive";
import { getBjtNowParts, loadDebugTime, resolveNowState } from "../lib/bjt";
import { loadArchiveDay, loadArchiveIndex } from "../lib/data";
import { useT } from "../lib/ui-settings";
import type { ArchiveIndex, IndexItem, TodayIssue } from "../lib/types";

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

interface ArchiveRecord {
  entry: IndexItem;
  issue: TodayIssue | null;
  error: string | null;
}

function archiveDayId(entry: IndexItem) {
  return `archive-day-${entry.date.replace(/[^a-zA-Z0-9_-]/g, "-")}`;
}

export function ArchiveRoute() {
  const tx = useT();
  const hudContext = useContext(HudContext);

  // IMPORTANT:
  // Do NOT put `hudContext` into effects' dependency arrays.
  // `updateHud()` changes HUD state -> Provider value changes -> `hudContext` identity changes.
  const updateHudRef = useRef(hudContext?.updateHud);
  useEffect(() => {
    updateHudRef.current = hudContext?.updateHud;
  }, [hudContext?.updateHud]);

  const [index, setIndex] = useState<ArchiveIndex | null>(null);
  const [records, setRecords] = useState<ArchiveRecord[]>([]);
  const [indexError, setIndexError] = useState<string | null>(null);
  const [nowState, setNowState] = useState(() =>
    resolveNowState(getBjtNowParts(loadDebugTime()).secondsSinceMidnight).state
  );
  const prefersReducedMotion = useReducedMotion();

  useEffect(() => {
    let active = true;
    setIndexError(null);

    loadArchiveIndex()
      .then((data) => {
        if (!active) return;
        setIndex(data);
        const recentEntries = getRecentArchiveEntries(data);
        setRecords(recentEntries.map((entry) => ({ entry, issue: null, error: null })));
      })
      .catch((err: Error) => {
        if (!active) return;
        setIndexError(err.message);
      });

    return () => {
      active = false;
    };
  }, []);

  const recentEntries = useMemo(() => (index ? getRecentArchiveEntries(index) : []), [index]);
  const archiveRetentionDays = index?.archive_retention_days ?? DEFAULT_ARCHIVE_RETENTION_DAYS;

  useEffect(() => {
    if (!recentEntries.length) {
      return;
    }

    let active = true;
    setRecords(recentEntries.map((entry) => ({ entry, issue: null, error: null })));

    Promise.all(
      recentEntries.map(async (entry): Promise<ArchiveRecord> => {
        try {
          const issue = await loadArchiveDay(entry.date, entry.run_id);
          return { entry, issue, error: null };
        } catch (err) {
          return {
            entry,
            issue: null,
            error: err instanceof Error ? err.message : String(err)
          };
        }
      })
    ).then((nextRecords) => {
      if (!active) return;
      setRecords(nextRecords);
    });

    return () => {
      active = false;
    };
  }, [recentEntries]);

  useEffect(() => {
    const tick = () => {
      setNowState(resolveNowState(getBjtNowParts(loadDebugTime()).secondsSinceMidnight).state);
    };
    tick();
    const timer = window.setInterval(tick, 500);
    return () => window.clearInterval(timer);
  }, []);

  useEffect(() => {
    const loadedIssues = records.map((record) => record.issue).filter((issue): issue is TodayIssue => Boolean(issue));
    const marqueeItems = loadedIssues
      .flatMap((issue) => issue.picks.map((pick) => `${pick.title} — ${pick.artist_credit}`))
      .slice(0, 12);

    updateHudRef.current?.({
      status: indexError ? "ERROR" : nowState === "OFFLINE" ? "ARCHIVE" : "OK",
      marqueeItems,
      statusMessage: nowState === "OFFLINE" ? tx("archive.offlineMode") : null
    });
  }, [indexError, nowState, records, tx]);

  const scrollToDay = (entry: IndexItem) => {
    document.getElementById(archiveDayId(entry))?.scrollIntoView({
      behavior: prefersReducedMotion ? "auto" : "smooth",
      block: "start"
    });
  };

  if (indexError) {
    return <BSOD message={`${tx("system.errors.archiveLoad")}: ${indexError}`} />;
  }

  return (
    <section className="flex flex-col gap-8">
      <div className="section-toolbar flex flex-wrap items-start justify-between gap-4">
        <div className="flex flex-col gap-2">
          <p className="ui-kicker text-clinical-white/60">{tx("archive.label")}</p>
          <h1 className="text-3xl font-semibold uppercase tracking-tightish">{tx("archive.recentTitle")}</h1>
          <p className="font-mono text-sm text-clinical-white/60">{tx("archive.recentIntro")}</p>
          {recentEntries.length > 0 && recentEntries.length < archiveRetentionDays ? (
            <p className="font-mono text-xs uppercase tracking-[0.22em] text-clinical-white/50">
              {tx("archive.partialHint")}
            </p>
          ) : null}
        </div>
        <Link
          to="/"
          className="ui-button border-panel-700/80 text-clinical-white/70 hover:border-signal-accent/60 hover:text-signal-accent"
        >
          {tx("archive.openToday")}
        </Link>
      </div>

      <div className="archive-layout grid gap-8 lg:grid-cols-[minmax(14rem,18rem)_1fr]">
        <div className="hud-border rounded-card bg-panel-900/70 p-4">
          <p className="ui-kicker text-clinical-white/50">{tx("archive.datesLabel")}</p>
          {recentEntries.length ? (
            <motion.ul
              className="archive-date-list mt-4 flex max-h-[420px] flex-col gap-2 overflow-auto pr-2 text-sm"
              variants={prefersReducedMotion ? undefined : listVariants}
              initial={prefersReducedMotion ? undefined : "hidden"}
              animate={prefersReducedMotion ? undefined : "show"}
            >
              {recentEntries.map((item) => (
                <motion.li
                  key={`${item.date}-${item.run_id ?? "legacy"}`}
                  variants={prefersReducedMotion ? undefined : itemVariants}
                >
                  <button
                    type="button"
                    onClick={() => scrollToDay(item)}
                    className="w-full rounded-hud border border-panel-700/70 px-3 py-3 text-left font-mono text-[0.76rem] uppercase tracking-[0.22em] text-clinical-white/60 transition hover:border-clinical-white/40 hover:text-signal-accent"
                  >
                    <span>{item.date}</span>
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
            <p className="mt-4 font-mono text-xs text-clinical-white/50">
              {index ? tx("archive.noRecent") : tx("archive.loadingIndex")}
            </p>
          )}
        </div>

        <div className="flex min-w-0 flex-col gap-6">
          {records.length ? (
            records.map((record) => {
              const issue = record.issue;
              const slots = issue ? getArchiveIssueSlots(issue) : [];
              const cacheKey = issue?.run_id ?? issue?.date ?? record.entry.run_id ?? record.entry.date;
              return (
                <article
                  key={`${record.entry.date}-${record.entry.run_id ?? "legacy"}`}
                  id={archiveDayId(record.entry)}
                  style={{ scrollMarginTop: "calc(var(--hud-height, 168px) + 1.5rem)" }}
                  className="hud-border rounded-card bg-panel-900/70 p-4 sm:p-5"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="ui-kicker text-clinical-white/50">{tx("archive.dayLabel")}</p>
                      <h2 className="text-2xl font-semibold uppercase tracking-tightish">
                        {record.entry.date}
                        {record.entry.theme_of_day ? (
                          <span className="text-clinical-white/50"> · {record.entry.theme_of_day}</span>
                        ) : null}
                      </h2>
                    </div>
                    {record.entry.run_id ? (
                      <span className="rounded-full border border-panel-700/70 px-3 py-2 font-mono text-[10px] uppercase tracking-[0.24em] text-clinical-white/45">
                        {record.entry.run_id}
                      </span>
                    ) : null}
                  </div>

                  {record.error ? (
                    <div className="mt-5 rounded-card border border-alert-red/40 bg-panel-900/60 p-4 font-mono text-sm text-alert-red">
                      {tx("archive.missingDay")}: {record.error}
                    </div>
                  ) : null}

                  {!record.error && !issue ? (
                    <div className="mt-5 hud-border rounded-card bg-panel-900/60 p-6 font-mono text-sm text-clinical-white/60">
                      {tx("archive.loadingDay")}
                    </div>
                  ) : null}

                  {issue ? (
                    <div className="mt-5 flex flex-col gap-5">
                      {slots.map((slot) => (
                        <section key={slot.slot_id} className="rounded-card border border-panel-700/70 p-4">
                          <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
                            <div>
                              <p className="font-mono text-xs uppercase tracking-[0.28em] text-signal-accent">
                                {slot.window_label}
                              </p>
                              <p className="mt-1 text-[11px] uppercase tracking-[0.2em] text-clinical-white/50">
                                {slot.theme}
                              </p>
                            </div>
                            <span className="font-mono text-[10px] uppercase tracking-[0.24em] text-clinical-white/40">
                              {tx("archive.slotLabel")} {slot.slot_id + 1}
                            </span>
                          </div>
                          <div className="album-grid grid gap-6 md:grid-cols-3">
                            {slot.picks.map((pick) => (
                              <SlotCard
                                key={`${record.entry.date}-${slot.slot_id}-${pick.slot}`}
                                pick={pick}
                                cacheKey={pick.cover.cover_version ?? cacheKey}
                              />
                            ))}
                          </div>
                        </section>
                      ))}
                    </div>
                  ) : null}
                </article>
              );
            })
          ) : (
            <div className="hud-border rounded-card bg-panel-900/60 p-6 font-mono text-sm text-clinical-white/60">
              {index ? tx("archive.noRecent") : tx("archive.loadingIndex")}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
