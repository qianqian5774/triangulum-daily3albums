import type { KeyboardEvent, MouseEvent } from "react";
import { useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, LayoutGroup, motion, useReducedMotion } from "framer-motion";
import { HudContext } from "../App";
import { BSOD } from "../components/BSOD";
import { SlotCard } from "../components/SlotCard";
import { TreatmentViewerOverlay } from "../components/TreatmentViewerOverlay";
import { FLAGS } from "../config/flags";
import { loadArchiveDay, loadToday } from "../lib/data";
import { resolveCoverUrl } from "../lib/covers";
import {
  addDays,
  formatDebugTime,
  getBjtNowParts,
  loadDebugTime,
  resolveNowState,
  saveDebugTime,
  shiftDebugTime
} from "../lib/bjt";
import { parseTodayIssue, type TodayIssue, type TodaySlot } from "../lib/types";
import { t } from "../strings/t";
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

const LAST_GOOD_KEY = "lastGoodTodayJson";
const LAST_GOOD_DATE_KEY = "lastGoodDateKey";
const LAST_FETCHED_AT_KEY = "lastFetchedAtBjt";

const TRANSITION_DURATION_MS = 900;
const TRANSITION_SWAP_MS = 420;
const PRELOAD_TIMEOUT_MS = 2000;
const RETRY_FAST_MS = 5000;
const RETRY_SLOW_MS = 30000;
const RETRY_SLOW_AFTER_MS = 10 * 60 * 1000;

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

function getStoredLastGood(): TodayIssue | null {
  if (typeof window === "undefined") {
    return null;
  }
  const raw = window.localStorage.getItem(LAST_GOOD_KEY);
  if (!raw) {
    return null;
  }
  try {
    return parseTodayIssue(JSON.parse(raw));
  } catch {
    return null;
  }
}

function formatLastSuccess(issue?: TodayIssue | null) {
  if (!issue) {
    return null;
  }
  return issue.run_id ? `${issue.date} / ${issue.run_id}` : issue.date;
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

  const prefersReducedMotion = useReducedMotion();
  const [issue, setIssue] = useState<TodayIssue | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [focusedId, setFocusedId] = useState<string | null>(null);
  const [selectedSlotId, setSelectedSlotId] = useState<number | null>(null);
  const [direction, setDirection] = useState<-1 | 1>(1);
  const [glitchActive, setGlitchActive] = useState(false);
  const [ambientActive, setAmbientActive] = useState(false);
  const [signalState, setSignalState] = useState<"NORMAL" | "SIGNAL_LOST" | "RESTORED">("NORMAL");
  const [signalSince, setSignalSince] = useState<number | null>(null);
  const [lastRetryAt, setLastRetryAt] = useState<number | null>(null);
  const [archivedIssue, setArchivedIssue] = useState<TodayIssue | null>(null);
  const [archivedError, setArchivedError] = useState<string | null>(null);
  const [transitionActive, setTransitionActive] = useState(false);
  const [debugTime, setDebugTime] = useState<string | null>(() => loadDebugTime());
  const [bjtNow, setBjtNow] = useState(() => getBjtNowParts(loadDebugTime()));
  const [lastGoodIssue, setLastGoodIssue] = useState<TodayIssue | null>(() => getStoredLastGood());

  const lastActiveRef = useRef<HTMLElement | null>(null);
  const glitchTimeoutRef = useRef<number | null>(null);
  const idleTimeoutRef = useRef<number | null>(null);
  const lastFocusedRef = useRef<string | null>(null);
  const openingRef = useRef<string | null>(null);
  const transitionTimerRef = useRef<number | null>(null);
  const transitionSwapRef = useRef<number | null>(null);

  const coverCacheKey = issue?.run_id ?? issue?.date ?? lastGoodIssue?.run_id ?? lastGoodIssue?.date ?? "";

  useEffect(() => {
    const tick = () => {
      const stored = loadDebugTime();
      setDebugTime(stored);
      setBjtNow(getBjtNowParts(stored));
    };
    tick();
    const timer = window.setInterval(tick, 500);
    return () => window.clearInterval(timer);
  }, []);

  const nowStateInfo = useMemo(() => resolveNowState(bjtNow.secondsSinceMidnight), [bjtNow.secondsSinceMidnight]);
  const nowState = nowStateInfo.state;
  const nowSlotId = nowStateInfo.slotId;
  const prevStateRef = useRef(nowState);
  const prevSlotRef = useRef(nowSlotId);

  const needsArchiveFallback = nowState === "OFFLINE" || (signalState === "SIGNAL_LOST" && !lastGoodIssue);
  const displayIssue = signalState === "NORMAL" ? issue : lastGoodIssue ?? archivedIssue ?? issue;

  const slots = useMemo(() => {
    if (!displayIssue) {
      return [] as TodaySlot[];
    }
    if (displayIssue.slots?.length) {
      return displayIssue.slots;
    }
    return [
      {
        slot_id: displayIssue.now_slot_id ?? 0,
        window_label: "06:00–11:59",
        theme: displayIssue.theme_of_day,
        picks: displayIssue.picks
      }
    ];
  }, [displayIssue]);

  const activeSlot = useMemo(() => {
    if (!slots.length) {
      return null;
    }
    const match = slots.find((slot) => slot.slot_id === selectedSlotId);
    return match ?? slots[0];
  }, [slots, selectedSlotId]);

  const picks = useMemo(() => {
    if (!displayIssue) {
      return [];
    }
    const activePicks = activeSlot?.picks ?? displayIssue.picks;
    return activePicks.map((pick) => ({
      ...pick,
      stableId: deriveStableId(pick as { title: string; artist_credit: string; slot: string; id?: string })
    }));
  }, [activeSlot, displayIssue]);

  const headerText = useMemo(() => {
    if (!displayIssue) {
      return t("today.headerFallback");
    }
    return `${displayIssue.date} · ${t("today.themePrefix")} ${displayIssue.theme_of_day}`;
  }, [displayIssue]);

  const showReturnToNow =
    nowSlotId !== null && selectedSlotId !== null && selectedSlotId !== nowSlotId && nowState !== "OFFLINE";

  const showNowAvailable = showReturnToNow;

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

  const preloadSlotCovers = useCallback(
    async (slot: TodaySlot | undefined | null) => {
      if (!slot) {
        return;
      }
      const covers = slot.picks
        .map((pick) => resolveCoverUrl(pick.cover.optimized_cover_url, pick.cover.cover_version ?? coverCacheKey))
        .filter((url): url is string => Boolean(url));
      if (!covers.length) {
        return;
      }
      await Promise.race([
        Promise.all(
          covers.map(
            (url) =>
              new Promise<void>((resolve) => {
                const image = new Image();
                let done = false;
                const finish = () => {
                  if (done) return;
                  done = true;
                  resolve();
                };
                image.onload = finish;
                image.onerror = finish;
                image.src = url;
                if (image.decode) {
                  image.decode().then(finish).catch(finish);
                }
              })
          )
        ),
        new Promise<void>((resolve) => {
          window.setTimeout(resolve, PRELOAD_TIMEOUT_MS);
        })
      ]);
    },
    [coverCacheKey]
  );

  const runBoundaryTransition = useCallback(
    async (nextSlotId: number | null) => {
      if (nextSlotId === null) {
        setSelectedSlotId(null);
        return;
      }
      const nextSlot = slots.find((slot) => slot.slot_id === nextSlotId);
      if (!nextSlot || prefersReducedMotion) {
        setSelectedSlotId(nextSlotId);
        return;
      }
      await preloadSlotCovers(nextSlot);
      setTransitionActive(true);
      if (transitionSwapRef.current) {
        window.clearTimeout(transitionSwapRef.current);
      }
      if (transitionTimerRef.current) {
        window.clearTimeout(transitionTimerRef.current);
      }
      transitionSwapRef.current = window.setTimeout(() => {
        setSelectedSlotId(nextSlotId);
      }, TRANSITION_SWAP_MS);
      transitionTimerRef.current = window.setTimeout(() => {
        setTransitionActive(false);
      }, TRANSITION_DURATION_MS);
    },
    [prefersReducedMotion, preloadSlotCovers, slots]
  );

  const storeLastGood = useCallback(
    (payload: TodayIssue) => {
      if (typeof window === "undefined") {
        return;
      }
      window.localStorage.setItem(LAST_GOOD_KEY, JSON.stringify(payload));
      window.localStorage.setItem(LAST_GOOD_DATE_KEY, payload.date);
      window.localStorage.setItem(LAST_FETCHED_AT_KEY, formatDebugTime(bjtNow.parts));
      setLastGoodIssue(payload);
    },
    [bjtNow.parts]
  );

  const loadIssue = useCallback(
    async (options?: { cacheBust?: boolean; reason?: string }) => {
      setError(null);
      const cacheBust = options?.cacheBust ? Date.now().toString() : undefined;
      try {
        const data = await loadToday(cacheBust);
        const now = getBjtNowParts(loadDebugTime());
        if (data.date !== now.bjtDateKey) {
          setSignalState("SIGNAL_LOST");
          setSignalSince((prev) => prev ?? Date.now());
          return;
        }
        setIssue(data);
        storeLastGood(data);
        setSignalSince(null);
        if (signalState !== "NORMAL") {
          setSignalState("RESTORED");
        } else {
          setSignalState("NORMAL");
        }
      } catch (err) {
        const message = err instanceof Error ? err.message : String(err);
        setError(message);
        setSignalState("SIGNAL_LOST");
        setSignalSince((prev) => prev ?? Date.now());
      }
    },
    [signalState, storeLastGood]
  );

  const handleRetryNow = useCallback(() => {
    setLastRetryAt(Date.now());
    loadIssue({ cacheBust: true, reason: "manual" });
  }, [loadIssue]);

  // Load exactly once on mount.
  useEffect(() => {
    loadIssue();
  }, [loadIssue]);

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

  useEffect(() => {
    if (!slots.length) {
      return;
    }
    if (nowState === "OFFLINE") {
      setSelectedSlotId(null);
      return;
    }
    setSelectedSlotId((prev) => {
      if (prev === null) {
        return nowSlotId ?? slots[0]?.slot_id ?? null;
      }
      if (!slots.find((slot) => slot.slot_id === prev)) {
        return nowSlotId ?? slots[0]?.slot_id ?? prev;
      }
      return prev;
    });
  }, [nowState, nowSlotId, slots]);

  useEffect(() => {
    if (signalState !== "RESTORED") {
      return;
    }
    const timer = window.setTimeout(() => {
      setSignalState("NORMAL");
    }, 2500);
    return () => window.clearTimeout(timer);
  }, [signalState]);

  useEffect(() => {
    const prevState = prevStateRef.current;
    const prevSlot = prevSlotRef.current;
    const stateChanged = prevState !== nowState;
    const slotChanged = prevSlot !== nowSlotId;

    if (stateChanged || slotChanged) {
      if (nowState === "OFFLINE") {
        setSelectedSlotId(null);
      }
      if (prevState === "OFFLINE" && nowState !== "OFFLINE") {
        loadIssue({ cacheBust: true, reason: "boundary" });
      }
      if (prevSlot !== null && nowSlotId !== null && prevSlot !== nowSlotId) {
        if (selectedSlotId === prevSlot) {
          runBoundaryTransition(nowSlotId);
        }
      }
    }
    prevStateRef.current = nowState;
    prevSlotRef.current = nowSlotId;
  }, [loadIssue, nowSlotId, nowState, runBoundaryTransition, selectedSlotId]);

  useEffect(() => {
    if (!issue?.slots?.length) {
      return;
    }
    if (nowSlotId === null) {
      return;
    }
    const nextSlot = issue.slots.find((slot) => slot.slot_id === nowSlotId + 1);
    if (!nextSlot) {
      return;
    }
    const nextUnlockAt = nowSlotId === 0 ? 12 : 18;
    const secondsUntil = (nextUnlockAt * 3600) - bjtNow.secondsSinceMidnight;
    if (nowSlotId <= 1 || secondsUntil <= 5 * 60) {
      preloadSlotCovers(nextSlot);
    }
  }, [bjtNow.secondsSinceMidnight, issue?.slots, nowSlotId, preloadSlotCovers]);

  useEffect(() => {
    if (!needsArchiveFallback) {
      return;
    }
    const yesterdayKey = addDays(bjtNow.bjtDateKey, -1);
    setArchivedError(null);
    setArchivedIssue(null);
    loadArchiveDay(yesterdayKey)
      .then((data) => {
        setArchivedIssue(data);
      })
      .catch((err: Error) => {
        setArchivedError(err.message);
      });
  }, [bjtNow.bjtDateKey, needsArchiveFallback]);

  useEffect(() => {
    if (nowState === "OFFLINE") {
      return;
    }
    if (signalState !== "SIGNAL_LOST") {
      return;
    }
    const start = signalSince ?? Date.now();
    const elapsed = Date.now() - start;
    const interval = elapsed > RETRY_SLOW_AFTER_MS ? RETRY_SLOW_MS : RETRY_FAST_MS;
    const timer = window.setTimeout(() => {
      setLastRetryAt(Date.now());
      loadIssue({ cacheBust: true, reason: "retry" });
    }, interval);
    return () => window.clearTimeout(timer);
  }, [loadIssue, nowState, signalSince, signalState]);

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
      if (transitionSwapRef.current) {
        window.clearTimeout(transitionSwapRef.current);
      }
      if (transitionTimerRef.current) {
        window.clearTimeout(transitionTimerRef.current);
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

  const handleSelectSlot = (slotId: number) => {
    if (nowSlotId !== null && slotId > nowSlotId) {
      return;
    }
    setSelectedSlotId(slotId);
  };

  const applyDebugShift = (deltaSeconds: number) => {
    if (!debugTime) {
      return;
    }
    const next = shiftDebugTime(debugTime, deltaSeconds);
    if (!next) {
      return;
    }
    saveDebugTime(next);
    setDebugTime(next);
  };

  const clearDebug = () => {
    saveDebugTime(null);
    setDebugTime(null);
  };

  useEffect(() => {
    const marqueeSource =
      nowState === "OFFLINE" ? archivedIssue?.picks ?? [] : activeSlot?.picks ?? displayIssue?.picks ?? [];
    const marqueeItems = marqueeSource.map((pick) => `${pick.title} — ${pick.artist_credit}`);
    const statusMessage =
      signalState === "SIGNAL_LOST" && nowState !== "OFFLINE"
        ? t("today.offline.establishing")
        : signalState === "SIGNAL_LOST"
          ? t("today.offline.signalLost")
          : signalState === "RESTORED"
            ? t("today.offline.linkRestored")
            : nowState === "OFFLINE"
              ? t("today.offline.title")
              : null;
    updateHudRef.current?.({
      status: error ? "ERROR" : signalState === "SIGNAL_LOST" ? "DEGRADED" : "OK",
      marqueeItems,
      statusMessage,
      lastSuccess: formatLastSuccess(lastGoodIssue ?? issue)
    });
  }, [activeSlot, archivedIssue, displayIssue, error, issue, lastGoodIssue, nowState, signalState]);

  if (error && nowState !== "OFFLINE" && !displayIssue) {
    return <BSOD message={`${t("system.errors.todayLoad")}: ${error}`} />;
  }

  if (nowState === "OFFLINE") {
    return (
      <section className="relative flex flex-col gap-8">
        {transitionActive && <div className="transition-overlay" aria-hidden="true" />}
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="ambient-fade flex flex-col gap-2">
            <p className="text-xs uppercase tracking-[0.4em] text-clinical-white/60">{t("today.label")}</p>
            <h1 className="text-3xl font-semibold uppercase tracking-tightish text-alert-red">
              {t("today.offline.title")}
            </h1>
            <p className="font-mono text-sm text-clinical-white/60">{t("today.offline.nextBoot")}</p>
          </div>
          <div className="ambient-fade flex flex-wrap items-center gap-3">
            <a
              href="#/archive"
              className="rounded-full border border-acid-green/60 px-4 py-2 text-xs uppercase tracking-[0.3em] text-acid-green transition hover:border-acid-green hover:text-acid-green/90"
            >
              {t("today.offline.viewArchive")}
            </a>
          </div>
        </div>
        <div className="hud-border rounded-card bg-panel-900/60 p-6">
          <p className="text-xs uppercase tracking-[0.3em] text-clinical-white/50">
            {t("today.offline.archivedHint")}
          </p>
          <div className="relative mt-6">
            <span className="archived-watermark">{t("today.offline.archivedLabel")}</span>
            {archivedIssue ? (
              <a href="#/archive" className="block">
                <div className="pointer-events-none grid gap-6 md:grid-cols-3">
                  {archivedIssue.picks.map((pick) => (
                    <SlotCard
                      key={pick.slot}
                      pick={pick}
                      className="archived-card"
                      cacheKey={pick.cover.cover_version ?? archivedIssue.run_id ?? archivedIssue.date}
                      disableLinks
                    />
                  ))}
                </div>
              </a>
            ) : (
              <div className="hud-border rounded-card bg-panel-900/60 p-6 font-mono text-sm text-clinical-white/60">
                {archivedError ? t("today.offline.noSignal") : t("today.loading")}
              </div>
            )}
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className={`relative flex flex-col gap-8 ${ambientActive ? "ambient-mode" : ""}`}>
      {transitionActive && <div className="transition-overlay" aria-hidden="true" />}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="ambient-fade flex flex-col gap-2">
          <p className="text-xs uppercase tracking-[0.4em] text-clinical-white/60">{t("today.label")}</p>
          <h1 className="text-3xl font-semibold uppercase tracking-tightish">{headerText}</h1>
          <p className="font-mono text-sm text-clinical-white/60">{t("today.intro")}</p>
          {signalState === "SIGNAL_LOST" ? (
            <p className="mt-2 text-xs uppercase tracking-[0.35em] text-alert-red">
              {t("today.offline.signalLost")}
            </p>
          ) : null}
          {signalState === "RESTORED" ? (
            <p className="mt-2 text-xs uppercase tracking-[0.35em] text-acid-green">
              {t("today.offline.linkRestored")}
            </p>
          ) : null}
        </div>
        <div className="ambient-fade flex flex-wrap items-center gap-3">
          {showNowAvailable && (
            <span className="rounded-full border border-alert-red/60 px-3 py-2 text-[10px] uppercase tracking-[0.3em] text-alert-red">
              {t("today.nowAvailable")}
            </span>
          )}
          {showReturnToNow && (
            <button
              type="button"
              onClick={() => setSelectedSlotId(nowSlotId)}
              className="rounded-full border border-acid-green/60 px-4 py-2 text-xs uppercase tracking-[0.3em] text-acid-green transition hover:border-acid-green hover:text-acid-green/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-acid-green/70"
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

      {debugTime ? (
        <div className="hud-border rounded-card bg-panel-900/70 p-4 text-[11px] uppercase tracking-[0.25em] text-clinical-white/60">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span>{t("today.debug.label")}</span>
            <span className="font-mono text-xs text-acid-green">{debugTime}</span>
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              className="rounded-full border border-panel-700/70 px-3 py-2 text-[10px] uppercase tracking-[0.25em] text-clinical-white/70 hover:border-acid-green/60"
              onClick={() => applyDebugShift(60)}
            >
              {t("today.debug.addMinute")}
            </button>
            <button
              type="button"
              className="rounded-full border border-panel-700/70 px-3 py-2 text-[10px] uppercase tracking-[0.25em] text-clinical-white/70 hover:border-acid-green/60"
              onClick={() => applyDebugShift(3600)}
            >
              {t("today.debug.addHour")}
            </button>
            <button
              type="button"
              className="rounded-full border border-panel-700/70 px-3 py-2 text-[10px] uppercase tracking-[0.25em] text-clinical-white/70 hover:border-acid-green/60"
              onClick={() => applyDebugShift(86400)}
            >
              {t("today.debug.addDay")}
            </button>
            <button
              type="button"
              className="rounded-full border border-alert-red/60 px-3 py-2 text-[10px] uppercase tracking-[0.25em] text-alert-red hover:border-alert-red"
              onClick={clearDebug}
            >
              {t("today.debug.clear")}
            </button>
          </div>
        </div>
      ) : null}

      {displayIssue ? (
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
                  const isLocked = nowSlotId !== null ? slot.slot_id > nowSlotId : true;
                  return (
                    <button
                      key={slot.slot_id}
                      type="button"
                      disabled={isLocked}
                      onClick={() => handleSelectSlot(slot.slot_id)}
                      className={`flex w-full items-center gap-4 rounded-card border px-4 py-4 text-left transition ${
                        isActive
                          ? "border-acid-green/70 bg-panel-800/70 text-acid-green"
                          : isLocked
                            ? "border-panel-800/70 text-clinical-white/30"
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
                        <span className="text-xs uppercase tracking-[0.3em]">{slot.window_label}</span>
                        <span className="text-[11px] uppercase tracking-[0.2em] text-clinical-white/50">
                          {slot.theme}
                        </span>
                      </div>
                      {isLocked ? (
                        <span className="text-[10px] uppercase tracking-[0.3em] text-clinical-white/30">
                          {t("today.timeline.locked")}
                        </span>
                      ) : null}
                    </button>
                  );
                })}
              </div>
              {signalState === "SIGNAL_LOST" && nowState !== "OFFLINE" ? (
                <div className="mt-6 rounded-card border border-alert-red/40 bg-panel-900/80 p-4 text-[10px] uppercase tracking-[0.3em] text-alert-red">
                  <p>{t("today.offline.establishing")}</p>
                  {lastRetryAt ? (
                    <p className="mt-2 text-[9px] text-clinical-white/40">
                      {new Intl.DateTimeFormat("en-GB", {
                        timeZone: "Asia/Shanghai",
                        hour: "2-digit",
                        minute: "2-digit",
                        second: "2-digit",
                        hour12: false
                      }).format(new Date(lastRetryAt))}
                    </p>
                  ) : null}
                  <button
                    type="button"
                    onClick={handleRetryNow}
                    className="mt-3 rounded-full border border-alert-red/60 px-3 py-2 text-[10px] uppercase tracking-[0.25em] text-alert-red"
                  >
                    {t("today.offline.retry")}
                  </button>
                </div>
              ) : null}
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
