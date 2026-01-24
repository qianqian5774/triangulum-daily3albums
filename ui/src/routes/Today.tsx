import type { KeyboardEvent, MouseEvent } from "react";
import { useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, LayoutGroup, motion, useReducedMotion } from "framer-motion";
import { HudContext } from "../App";
import { BSOD } from "../components/BSOD";
import { SlotCard } from "../components/SlotCard";
import { TreatmentViewerOverlay } from "../components/TreatmentViewerOverlay";
import { FLAGS } from "../config/flags";
import { loadToday } from "../lib/data";
import { resolveCoverUrl } from "../lib/covers";
import { t } from "../strings/t";
import type { TodayIssue } from "../lib/types";
import type { TreatmentPick } from "../components/TreatmentViewerOverlay";

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
  const [selectedSlotId, setSelectedSlotId] = useState<number | null>(null);
  const [direction, setDirection] = useState<-1 | 1>(1);
  const [glitchActive, setGlitchActive] = useState(false);
  const [ambientActive, setAmbientActive] = useState(false);
  const prefersReducedMotion = useReducedMotion();
  const lastActiveRef = useRef<HTMLElement | null>(null);
  const glitchTimeoutRef = useRef<number | null>(null);
  const idleTimeoutRef = useRef<number | null>(null);
  const lastFocusedRef = useRef<string | null>(null);
  const openingRef = useRef<string | null>(null);
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

  const slots = useMemo(() => {
    if (!issue) {
      return [];
    }
    if (issue.slots?.length) {
      return issue.slots;
    }
    return [
      {
        slot_id: issue.now_slot_id ?? 0,
        label: t("today.timeline.nowLabel"),
        theme: issue.theme_of_day,
        picks: issue.picks
      }
    ];
  }, [issue]);

  useEffect(() => {
    if (!issue) {
      return;
    }
    const nextSlotId = issue.now_slot_id ?? slots[0]?.slot_id ?? 0;
    setSelectedSlotId(nextSlotId);
  }, [issue, slots]);

  const activeSlot = useMemo(() => {
    if (!slots.length) {
      return null;
    }
    const match = slots.find((slot) => slot.slot_id === selectedSlotId);
    return match ?? slots[0];
  }, [slots, selectedSlotId]);

  const picks = useMemo(() => {
    if (!issue) {
      return [];
    }
    const activePicks = activeSlot?.picks ?? issue.picks;
    return activePicks.map((pick) => ({
      ...pick,
      stableId: deriveStableId(pick as { title: string; artist_credit: string; slot: string; id?: string })
    }));
  }, [activeSlot, issue]);

  const headerText = useMemo(() => {
    if (!issue) {
      return t("today.headerFallback");
    }
    return `${issue.date} · ${t("today.themePrefix")} ${issue.theme_of_day}`;
  }, [issue]);

  const showReturnToNow =
    issue?.now_slot_id !== null &&
    issue?.now_slot_id !== undefined &&
    selectedSlotId !== null &&
    selectedSlotId !== issue.now_slot_id;

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

  useEffect(() => {
    if (!focusedId) {
      return;
    }
    setAmbientActive(false);
    if (idleTimeoutRef.current) {
      window.clearTimeout(idleTimeoutRef.current);
      idleTimeoutRef.current = null;
    }
  }, [focusedId]);

  const resetIdleTimer = useCallback(() => {
    if (focusedId) {
      return;
    }
    setAmbientActive(false);
    if (idleTimeoutRef.current) {
      window.clearTimeout(idleTimeoutRef.current);
    }
    idleTimeoutRef.current = window.setTimeout(() => {
      setAmbientActive(true);
    }, 60000);
  }, [focusedId]);

  useEffect(() => {
    const handleActivity = () => resetIdleTimer();
    const events = ["mousemove", "mousedown", "keydown", "touchstart", "pointerdown", "wheel"];
    events.forEach((eventName) => window.addEventListener(eventName, handleActivity, { passive: true }));
    resetIdleTimer();
    return () => {
      events.forEach((eventName) => window.removeEventListener(eventName, handleActivity));
      if (idleTimeoutRef.current) {
        window.clearTimeout(idleTimeoutRef.current);
      }
    };
  }, [resetIdleTimer]);

  const preloadCover = useCallback(
    async (pick: TreatmentPick | undefined) => {
      if (!pick) {
        return;
      }
      const coverVersionKey = pick.cover.cover_version ?? coverCacheKey;
      const coverUrl = resolveCoverUrl(pick.cover.optimized_cover_url, coverVersionKey);
      if (!coverUrl) {
        return;
      }
      await new Promise<void>((resolve) => {
        const image = new Image();
        let done = false;
        const finish = () => {
          if (done) return;
          done = true;
          resolve();
        };
        image.onload = finish;
        image.onerror = finish;
        image.src = coverUrl;
        if (image.decode) {
          image.decode().then(finish).catch(finish);
        }
      });
    },
    [coverCacheKey]
  );

  const openPick = useCallback(
    async (pickId: string) => {
      const nextPick = picks.find((pick) => pick.stableId === pickId);
      openingRef.current = pickId;
      await preloadCover(nextPick);
      if (openingRef.current !== pickId) {
        return;
      }
      setFocusedId(pickId);
    },
    [picks, preloadCover]
  );

  const handleOpen = (pickId: string, event: MouseEvent<HTMLElement> | KeyboardEvent<HTMLElement>) => {
    lastActiveRef.current = event.currentTarget as HTMLElement;
    setDirection(1);
    openPick(pickId);
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

  useEffect(() => {
    if (!picks.length) {
      return;
    }
    const warm = picks.slice(0, 3);
    warm.forEach((pick) => {
      const coverVersionKey = pick.cover.cover_version ?? coverCacheKey;
      const coverUrl = resolveCoverUrl(pick.cover.optimized_cover_url, coverVersionKey);
      if (!coverUrl) {
        return;
      }
      const image = new Image();
      image.src = coverUrl;
      if (image.decode) {
        image.decode().catch(() => undefined);
      }
    });
  }, [coverCacheKey, picks]);

  const handleNext = () => {
    if (!picks.length) return;
    const nextIndex = (activeIndex + 1) % picks.length;
    setDirection(1);
    openPick(picks[nextIndex].stableId);
    triggerGlitch(80);
  };

  const handlePrev = () => {
    if (!picks.length) return;
    const nextIndex = (activeIndex - 1 + picks.length) % picks.length;
    setDirection(-1);
    openPick(picks[nextIndex].stableId);
    triggerGlitch(80);
  };

  if (error) {
    return <BSOD message={`${t("system.errors.todayLoad")}: ${error}`} />;
  }

  return (
    <section className={`flex flex-col gap-8 ${ambientActive ? "ambient-mode" : ""}`}>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="ambient-fade flex flex-col gap-2">
          <p className="text-xs uppercase tracking-[0.4em] text-clinical-white/60">{t("today.label")}</p>
          <h1 className="text-3xl font-semibold uppercase tracking-tightish">{headerText}</h1>
          <p className="font-mono text-sm text-clinical-white/60">{t("today.intro")}</p>
        </div>
        <div className="ambient-fade flex flex-wrap items-center gap-3">
          {showReturnToNow && (
            <button
              type="button"
              onClick={() => setSelectedSlotId(issue?.now_slot_id ?? null)}
              className="rounded-full border border-acid-green/50 px-4 py-2 text-xs uppercase tracking-[0.3em] text-acid-green transition hover:border-acid-green hover:text-acid-green/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-acid-green/70"
            >
              {t("today.returnToNow")}
            </button>
          )}
          <button
            type="button"
            onClick={() => setAmbientActive((prev) => !prev)}
            disabled={Boolean(focusedId)}
            data-testid="ambient-toggle"
            className="rounded-full border border-panel-700/80 px-4 py-2 text-xs uppercase tracking-[0.3em] text-clinical-white/70 transition hover:border-acid-green/60 hover:text-acid-green disabled:cursor-not-allowed disabled:border-panel-700/40 disabled:text-clinical-white/40"
          >
            {ambientActive ? t("today.ambientExit") : t("today.ambientEnter")}
          </button>
        </div>
      </div>

      {issue ? (
        <LayoutGroup>
          <div className="grid gap-10 lg:grid-cols-[280px_1fr]">
            <aside className="ambient-fade hud-border rounded-card bg-panel-900/70 p-5">
              <p className="text-sm uppercase tracking-[0.35em] text-clinical-white/60">
                {t("today.timeline.title")}
              </p>
              <div className="mt-5 flex flex-col gap-4">
                {slots.map((slot) => {
                  const isActive = slot.slot_id === (activeSlot?.slot_id ?? slot.slot_id);
                  const thumbPick = slot.picks[0];
                  const thumbUrl = thumbPick
                    ? resolveCoverUrl(
                        thumbPick.cover.optimized_cover_url,
                        thumbPick.cover.cover_version ?? coverCacheKey
                      )
                    : null;
                  return (
                    <button
                      key={slot.slot_id}
                      type="button"
                      onClick={() => setSelectedSlotId(slot.slot_id)}
                      className={`flex w-full items-center gap-4 rounded-card border px-4 py-4 text-left transition ${
                        isActive
                          ? "border-acid-green/70 bg-panel-800/70 text-acid-green"
                          : "border-panel-700/70 text-clinical-white/70 hover:border-clinical-white/60"
                      }`}
                    >
                      <div className="h-14 w-14 overflow-hidden rounded-md border border-panel-700/60 bg-panel-800">
                        {thumbUrl ? (
                          <img src={thumbUrl} alt="" className="h-full w-full object-cover" />
                        ) : (
                          <div className="flex h-full w-full items-center justify-center text-[8px] uppercase tracking-[0.3em] text-clinical-white/30">
                            {t("today.timeline.thumb")}
                          </div>
                        )}
                      </div>
                      <div className="flex flex-1 flex-col gap-1">
                        <span className="text-xs uppercase tracking-[0.3em]">
                          {slot.label}
                        </span>
                        <span className="text-[11px] uppercase tracking-[0.2em] text-clinical-white/50">
                          {slot.theme}
                        </span>
                      </div>
                    </button>
                  );
                })}
              </div>
            </aside>
            <motion.div
              className={`grid gap-6 md:grid-cols-3 xl:gap-8 ${FLAGS.dominantViewport ? "md:h-[78vh]" : ""}`}
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
                    imageLoading={index < 3 ? "eager" : "lazy"}
                    fetchPriority={index < 3 ? "high" : "auto"}
                  />
                </motion.div>
              ))}
            </motion.div>
          </div>

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
