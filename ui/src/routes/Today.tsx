import type { KeyboardEvent, MouseEvent } from "react";
import { useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, LayoutGroup, motion, useReducedMotion } from "framer-motion";
import { HudContext } from "../App";
import { BSOD } from "../components/BSOD";
import { SlotCard } from "../components/SlotCard";
import { TreatmentViewerOverlay } from "../components/TreatmentViewerOverlay";
import { FLAGS } from "../config/flags";
import { loadToday } from "../lib/data";
import { t } from "../strings/t";
import type { TodayIssue } from "../lib/types";

const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.18
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

function hashPick(value: string) {
  let hash = 0;
  for (let i = 0; i < value.length; i += 1) {
    hash = (hash << 5) - hash + value.charCodeAt(i);
    hash |= 0;
  }
  return Math.abs(hash).toString(36);
}

function deriveStableId(pick: { title: string; artist_credit: string; slot: string; id?: string }) {
  if (pick.id && pick.id.trim()) {
    return pick.id;
  }
  return `slot-${hashPick(`${pick.title}—${pick.artist_credit}—${pick.slot}`)}`;
}

export function TodayRoute() {
  const hudContext = useContext(HudContext);

  /**
   * Critical: do NOT put the entire hudContext object into the data-loading effect deps.
   * HUD state may update frequently (clock / flicker / status), recreating the context value,
   * which would retrigger the effect and spam-fetch today.json.
   *
   * We keep only a ref to the latest updateHud function.
   */
  const updateHudRef = useRef(hudContext?.updateHud);
  useEffect(() => {
    updateHudRef.current = hudContext?.updateHud;
  }, [hudContext?.updateHud]);

  const [issue, setIssue] = useState<TodayIssue | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [focusedId, setFocusedId] = useState<string | null>(null);
  const [direction, setDirection] = useState<-1 | 1>(1);
  const [glitchActive, setGlitchActive] = useState(false);
  const prefersReducedMotion = useReducedMotion();
  const lastActiveRef = useRef<HTMLElement | null>(null);
  const glitchTimeoutRef = useRef<number | null>(null);
  const lastFocusedRef = useRef<string | null>(null);
  const coverCacheKey = issue?.run_id ?? issue?.date ?? "";

  const loadIssue = useCallback(() => {
    let active = true;

    loadToday()
      .then((data) => {
        if (!active) return;

        setIssue(data);

        const batchId = data.run_id ? data.run_id.toUpperCase() : data.date;
        const marqueeItems = data.picks.map((pick) => `${pick.title} — ${pick.artist_credit}`);
        const nextRefreshAt =
          typeof (data as Record<string, unknown>).next_refresh_at === "string"
            ? ((data as Record<string, unknown>).next_refresh_at as string)
            : null;

        updateHudRef.current?.({
          batchId,
          status: "OK",
          marqueeItems,
          nextRefreshAt
        });
      })
      .catch((err: Error) => {
        if (!active) return;
        setError(err.message);
        updateHudRef.current?.({ status: "ERROR" });
      });

    return () => {
      active = false;
    };
  }, []);

  // Load exactly once on mount.
  useEffect(() => loadIssue(), [loadIssue]);

  useEffect(() => {
    const handleRefresh = () => {
      if (document.visibilityState === "visible") {
        loadIssue();
      }
    };

    window.addEventListener("focus", handleRefresh);
    document.addEventListener("visibilitychange", handleRefresh);

    return () => {
      window.removeEventListener("focus", handleRefresh);
      document.removeEventListener("visibilitychange", handleRefresh);
    };
  }, [loadIssue]);

  const picks = useMemo(() => {
    if (!issue) {
      return [];
    }
    return issue.picks.map((pick) => ({
      ...pick,
      stableId: deriveStableId(pick as { title: string; artist_credit: string; slot: string; id?: string })
    }));
  }, [issue]);

  const headerText = useMemo(() => {
    if (!issue) {
      return t("today.headerFallback");
    }
    return `${issue.date} · ${t("today.themePrefix")} ${issue.theme_of_day}`;
  }, [issue]);

  const activeIndex = useMemo(() => {
    if (!focusedId) {
      return 0;
    }
    const index = picks.findIndex((pick) => pick.stableId === focusedId);
    return index >= 0 ? index : 0;
  }, [focusedId, picks]);

  const triggerGlitch = (duration: number) => {
    if (prefersReducedMotion || !FLAGS.organicGlitch) {
      return;
    }
    if (glitchTimeoutRef.current) {
      window.clearTimeout(glitchTimeoutRef.current);
    }
    setGlitchActive(true);
    glitchTimeoutRef.current = window.setTimeout(() => {
      setGlitchActive(false);
    }, duration);
  };

  useEffect(() => {
    if (!focusedId || lastFocusedRef.current) {
      lastFocusedRef.current = focusedId;
      return;
    }
    triggerGlitch(120);
    lastFocusedRef.current = focusedId;
  }, [focusedId]);

  useEffect(
    () => () => {
      if (glitchTimeoutRef.current) {
        window.clearTimeout(glitchTimeoutRef.current);
      }
    },
    []
  );

  const handleOpen = (pickId: string, event: MouseEvent<HTMLElement> | KeyboardEvent<HTMLElement>) => {
    lastActiveRef.current = event.currentTarget as HTMLElement;
    setDirection(1);
    setFocusedId(pickId);
  };

  const handleClose = () => {
    setFocusedId(null);
    setGlitchActive(false);
    if (glitchTimeoutRef.current) {
      window.clearTimeout(glitchTimeoutRef.current);
      glitchTimeoutRef.current = null;
    }
    window.requestAnimationFrame(() => lastActiveRef.current?.focus());
  };

  const handleNext = () => {
    if (!picks.length) return;
    const nextIndex = (activeIndex + 1) % picks.length;
    setDirection(1);
    setFocusedId(picks[nextIndex].stableId);
    triggerGlitch(80);
  };

  const handlePrev = () => {
    if (!picks.length) return;
    const nextIndex = (activeIndex - 1 + picks.length) % picks.length;
    setDirection(-1);
    setFocusedId(picks[nextIndex].stableId);
    triggerGlitch(80);
  };

  if (error) {
    return <BSOD message={`${t("system.errors.todayLoad")}: ${error}`} />;
  }

  return (
    <section className="flex flex-col gap-8">
      <div className="flex flex-col gap-2">
        <p className="text-xs uppercase tracking-[0.4em] text-clinical-white/60">{t("today.label")}</p>
        <h1 className="text-3xl font-semibold uppercase tracking-tightish">{headerText}</h1>
        <p className="font-mono text-sm text-clinical-white/60">{t("today.intro")}</p>
      </div>

      {issue ? (
        <LayoutGroup>
          <motion.div
            className={`grid gap-6 md:grid-cols-3 ${FLAGS.dominantViewport ? "md:h-[78vh]" : ""}`}
            variants={prefersReducedMotion ? undefined : containerVariants}
            initial={prefersReducedMotion ? undefined : "hidden"}
            animate={prefersReducedMotion ? undefined : "show"}
          >
            {picks.map((pick, index) => (
              <motion.div key={pick.stableId} variants={prefersReducedMotion ? undefined : cardVariants}>
                <SlotCard
                  pick={pick}
                  layoutId={FLAGS.viewerOverlay ? `card-${pick.stableId}` : undefined}
                  onSelect={FLAGS.viewerOverlay ? (event) => handleOpen(pick.stableId, event) : undefined}
                  dataTestId={`album-card-${index}`}
                  className="h-full"
                  cacheKey={pick.cover.cover_version ?? coverCacheKey}
                />
              </motion.div>
            ))}
          </motion.div>

          <AnimatePresence>
            {FLAGS.viewerOverlay && focusedId && (
              <TreatmentViewerOverlay
                picks={picks}
                activeId={focusedId}
                direction={direction}
                onClose={handleClose}
                onNext={handleNext}
                onPrev={handlePrev}
                glitchActive={glitchActive}
                cacheKey={coverCacheKey}
              />
            )}
          </AnimatePresence>
        </LayoutGroup>
      ) : (
        <div className="hud-border rounded-card bg-panel-900/60 p-6 font-mono text-sm text-clinical-white/60">
          {t("today.loading")}
        </div>
      )}
    </section>
  );
}
