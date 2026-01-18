import { useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { LayoutGroup, motion, useReducedMotion } from "framer-motion";
import { useTranslation } from "react-i18next";
import { HudContext } from "../App";
import { BSOD } from "../components/BSOD";
import { SlotCard } from "../components/SlotCard";
import { TreatmentViewer } from "../components/TreatmentViewer";
import { FLAGS } from "../config/flags";
import { loadToday } from "../lib/data";
import type { PickItem, TodayIssue } from "../lib/types";

const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.15
    }
  }
};

const cardVariants = {
  hidden: { opacity: 0, y: -50 },
  show: {
    opacity: 1,
    y: 0,
    transition: {
      type: "spring",
      damping: 14,
      stiffness: 120,
      mass: 1.2
    }
  }
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

export function TodayRoute() {
  const hudContext = useContext(HudContext);
  const [issue, setIssue] = useState<TodayIssue | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [direction, setDirection] = useState<-1 | 1>(1);
  const prefersReducedMotion = useReducedMotion();
  const { t } = useTranslation();
  const cardRefs = useRef<Record<string, HTMLButtonElement | null>>({});
  const lastActiveRef = useRef<HTMLButtonElement | null>(null);

  const fetchIssue = useCallback(() => {
    let active = true;
    setError(null);
    loadToday()
      .then((data) => {
        if (!active) return;
        setIssue(data);
        const batchId = data.run_id ? data.run_id.toUpperCase() : data.date;
        const marqueeItems = data.picks.map((pick) => `${pick.title} — ${pick.artist_credit}`);
        hudContext?.updateHud({
          batchId,
          status: "OK",
          marqueeItems
        });
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

  useEffect(() => fetchIssue(), [fetchIssue]);

  const headerText = useMemo(() => {
    if (!issue) {
      return t("today.loading");
    }
    return t("today.headline", { date: issue.date, theme: issue.theme_of_day });
  }, [issue, t]);

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

  useEffect(() => {
    setActiveId(null);
  }, [issue?.date]);

  if (error) {
    return <BSOD message={t("system.error.today", { error })} />;
  }

  return (
    <section className="flex flex-col gap-8">
      <div className="flex flex-col gap-2">
        <p className="text-xs uppercase tracking-[0.4em] text-clinical-white/60">{t("today.label")}</p>
        <h1 className="text-3xl font-semibold uppercase tracking-tightish">{headerText}</h1>
        <p className="font-mono text-sm text-clinical-white/60">{t("today.helper")}</p>
        {issue && (
          <button
            type="button"
            onClick={() => fetchIssue()}
            className="mt-2 w-fit rounded-hud border border-panel-700/70 px-3 py-2 font-mono text-xs uppercase tracking-[0.3em] text-clinical-white/60 transition hover:border-clinical-white/40"
          >
            {t("today.readminister")}
          </button>
        )}
      </div>
      {issue ? (
        <LayoutGroup>
          <motion.div
            className="grid gap-6 md:grid-cols-3 md:gap-8 md:h-[75vh] md:auto-rows-fr"
            variants={prefersReducedMotion ? undefined : containerVariants}
            initial={prefersReducedMotion ? undefined : "hidden"}
            animate={prefersReducedMotion ? undefined : "show"}
          >
            {issue.picks.map((pick, index) => {
              const id = pickIds[index];
              return (
                <motion.div key={id} variants={prefersReducedMotion ? undefined : cardVariants} className="h-full">
                  <SlotCard
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
                </motion.div>
              );
            })}
          </motion.div>
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
          {t("today.loading_capsules")}
        </div>
      )}
    </section>
  );
}
