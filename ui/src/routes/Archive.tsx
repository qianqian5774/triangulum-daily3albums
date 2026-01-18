import { useContext, useEffect, useMemo, useRef, useState } from "react";
import { LayoutGroup, motion, useReducedMotion } from "framer-motion";
import { useTranslation } from "react-i18next";
import { HudContext } from "../App";
import { BSOD } from "../components/BSOD";
import { SlotCard } from "../components/SlotCard";
import { TreatmentViewer } from "../components/TreatmentViewer";
import { FLAGS } from "../config/flags";
import { loadArchiveDay, loadArchiveIndex } from "../lib/data";
import type { ArchiveIndex, PickItem, TodayIssue } from "../lib/types";

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

function hashString(value: string) {
  let hash = 0;
  for (let i = 0; i < value.length; i += 1) {
    hash = (hash * 31 + value.charCodeAt(i)) % 1_000_000_007;
  }
  return Math.abs(hash).toString(36);
}

function getStableId(pick: PickItem) {
  const base = pick.links?.musicbrainz || `${pick.artist_credit}-${pick.title}`;
  return hashString(base.trim().toLowerCase());
}

export function ArchiveRoute() {
  const hudContext = useContext(HudContext);
  const [index, setIndex] = useState<ArchiveIndex | null>(null);
  const [issue, setIssue] = useState<TodayIssue | null>(null);
  const [selectedDate, setSelectedDate] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [direction, setDirection] = useState<-1 | 1>(1);
  const prefersReducedMotion = useReducedMotion();
  const { t } = useTranslation();
  const cardRefs = useRef<Record<string, HTMLButtonElement | null>>({});
  const lastActiveRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    let active = true;
    loadArchiveIndex()
      .then((data) => {
        if (!active) return;
        setIndex(data);
        setSelectedDate(data.items[0]?.date ?? null);
      })
      .catch((err: Error) => {
        if (!active) return;
        setError(err.message);
        hudContext?.updateHud({ status: "ERROR" });
      });
    return () => {
      active = false;
    };
  }, [hudContext]);

  useEffect(() => {
    if (!selectedDate) {
      return;
    }
    let active = true;
    setActiveId(null);
    setError(null);
    loadArchiveDay(selectedDate)
      .then((data) => {
        if (!active) return;
        setIssue(data);
        hudContext?.updateHud({
          batchId: data.run_id ? data.run_id.toUpperCase() : data.date,
          status: "OK",
          marqueeItems: data.picks.map((pick) => `${pick.title} — ${pick.artist_credit}`)
        });
      })
      .catch((err: Error) => {
        if (!active) return;
        setIssue(null);
        setError(err.message);
        hudContext?.updateHud({ status: "ERROR" });
      });
    return () => {
      active = false;
    };
  }, [selectedDate, hudContext]);

  const headerText = useMemo(() => {
    if (!selectedDate) {
      return t("archive.header_fallback");
    }
    const theme = index?.items.find((item) => item.date === selectedDate)?.theme_of_day;
    return theme ? t("archive.header", { date: selectedDate, theme }) : selectedDate;
  }, [selectedDate, index, t]);

  const pickIds = useMemo(() => issue?.picks.map(getStableId) ?? [], [issue]);
  const activeIndex = activeId ? pickIds.indexOf(activeId) : -1;

  const openOverlay = (id: string) => {
    lastActiveRef.current = cardRefs.current[id];
    setDirection(1);
    setActiveId(id);
  };

  const closeOverlay = () => {
    setActiveId(null);
    requestAnimationFrame(() => {
      lastActiveRef.current?.focus();
    });
  };

  const navigateTo = (nextIndex: number) => {
    if (!issue) return;
    const nextId = pickIds[nextIndex];
    if (!nextId) return;
    setDirection(nextIndex > activeIndex ? 1 : -1);
    setActiveId(nextId);
  };

  if (error) {
    return <BSOD message={t("system.error.archive", { error })} />;
  }

  return (
    <section className="flex flex-col gap-8">
      <div className="flex flex-col gap-2">
        <p className="text-xs uppercase tracking-[0.4em] text-clinical-white/60">{t("archive.label")}</p>
        <h1 className="text-3xl font-semibold uppercase tracking-tightish">{headerText}</h1>
        <p className="font-mono text-sm text-clinical-white/60">{t("archive.helper")}</p>
      </div>
      <div className="grid gap-8 lg:grid-cols-[240px_1fr]">
        <div className="hud-border rounded-card bg-panel-900/70 p-4">
          <p className="text-xs uppercase tracking-[0.4em] text-clinical-white/50">{t("archive.drawer")}</p>
          {index ? (
            <motion.ul
              className="mt-4 flex max-h-[340px] flex-col gap-2 overflow-auto pr-2 text-sm"
              variants={prefersReducedMotion ? undefined : listVariants}
              initial={prefersReducedMotion ? undefined : "hidden"}
              animate={prefersReducedMotion ? undefined : "show"}
            >
              {index.items.map((item) => (
                <motion.li
                  key={item.date}
                  variants={prefersReducedMotion ? undefined : itemVariants}
                >
                  <button
                    type="button"
                    onClick={() => setSelectedDate(item.date)}
                    className={`w-full rounded-hud border px-3 py-2 text-left font-mono text-xs uppercase tracking-[0.3em] transition ${
                      selectedDate === item.date
                        ? "border-acid-green/70 text-acid-green"
                        : "border-panel-700/70 text-clinical-white/60 hover:border-clinical-white/40"
                    }`}
                  >
                    {item.date}
                  </button>
                </motion.li>
              ))}
            </motion.ul>
          ) : (
            <p className="mt-4 font-mono text-xs text-clinical-white/50">{t("archive.loading")}</p>
          )}
        </div>
        <div>
          {issue ? (
            <LayoutGroup>
              <div className="grid gap-6 md:grid-cols-3 md:gap-8">
                {issue.picks.map((pick, indexValue) => {
                  const id = pickIds[indexValue];
                  return (
                    <SlotCard
                      key={id}
                      pick={pick}
                      ref={(node) => {
                        if (id) {
                          cardRefs.current[id] = node;
                        }
                      }}
                      onSelect={() => openOverlay(id)}
                      layoutId={prefersReducedMotion ? undefined : `card-${id}`}
                      imageLayoutId={prefersReducedMotion ? undefined : `cover-${id}`}
                    />
                  );
                })}
              </div>
              {issue && FLAGS.viewerOverlay && activeId && activeIndex >= 0 ? (
                <TreatmentViewer
                  picks={issue.picks}
                  activeIndex={activeIndex}
                  activeId={activeId}
                  direction={direction}
                  reducedMotion={Boolean(prefersReducedMotion)}
                  onClose={closeOverlay}
                  onNavigate={navigateTo}
                />
              ) : null}
            </LayoutGroup>
          ) : (
            <div className="hud-border rounded-card bg-panel-900/60 p-6 font-mono text-sm text-clinical-white/60">
              {t("archive.select")}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
