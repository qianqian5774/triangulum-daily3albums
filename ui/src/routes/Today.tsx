import { useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, LayoutGroup, motion, useReducedMotion } from "framer-motion";
import { HudContext } from "../App";
import { BSOD } from "../components/BSOD";
import { AmbientOverlay } from "../components/AmbientOverlay";
import { ShareCardDialog } from "../components/ShareCardDialog";
import { SlotCard } from "../components/SlotCard";
import { TreatmentViewerOverlay } from "../components/TreatmentViewerOverlay";
import { FLAGS } from "../config/flags";
import { resolveCoverUrl } from "../lib/covers";
import { useProductClock } from "../lib/product-clock";
import { type TodaySlot } from "../lib/types";
import { useT } from "../lib/ui-settings";
import { useTodayData } from "../lib/use-today-data";
import { useTodayOverlayState } from "../lib/use-today-overlay-state";
import { useTodayPresentation } from "../lib/use-today-presentation";

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

const TRANSITION_DURATION_MS = 900;
const TRANSITION_SWAP_MS = 420;
const PRELOAD_TIMEOUT_MS = 2000;

export function TodayRoute() {
  const tx = useT();
  const hudContext = useContext(HudContext);
  const {
    bjtNow,
    clearDebug,
    debugPanelEnabled,
    debugTime,
    nowSlotId,
    nowState,
    setDebugClock,
    visualTheme
  } = useProductClock();

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
  const [transitionActive, setTransitionActive] = useState(false);

  const {
    archivedError,
    archivedIssue,
    displayIssue,
    error,
    issue,
    lastGoodIssue,
    lastRetryAt,
    loadIssue,
    retryNow,
    signalState
  } = useTodayData({ bjtDateKey: bjtNow.bjtDateKey, nowState });

  const transitionTimerRef = useRef<number | null>(null);
  const transitionSwapRef = useRef<number | null>(null);
  const {
    activeSlot,
    coverCacheKey,
    picks,
    returnToNow,
    selectSlot,
    selectedSlotId,
    setSelectedSlotId,
    showNowAvailable,
    showReturnToNow,
    slots
  } = useTodayPresentation({ displayIssue, issue, lastGoodIssue, nowSlotId, nowState });

  const {
    ambientActive,
    closeShare,
    direction,
    enterAmbient,
    exitAmbient,
    focusedId,
    glitchActive,
    handleClose,
    handleNext,
    handleOpen,
    handlePrev,
    lockedFeedback,
    openShare,
    shareOpen,
    triggerLockedFeedback
  } = useTodayOverlayState({ picks, prefersReducedMotion });

  const prevStateRef = useRef(nowState);
  const prevSlotRef = useRef(nowSlotId);

  const headerText = useMemo(() => {
    if (!displayIssue) {
      return tx("today.headerFallback");
    }
    return displayIssue.date;
  }, [displayIssue, tx]);

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

  useEffect(
    () => () => {
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

  useEffect(() => {
    const unlockedPicks =
      nowSlotId === null
        ? []
        : slots
            .filter((slot) => slot.slot_id <= nowSlotId)
            .flatMap((slot) => slot.picks);
    const marqueeSource =
      nowState === "OFFLINE"
        ? archivedIssue?.picks ?? []
        : unlockedPicks.length
          ? unlockedPicks
          : activeSlot?.picks ?? displayIssue?.picks ?? [];
    const marqueeItems = marqueeSource.map((pick) => `${pick.title} — ${pick.artist_credit}`);
    const statusMessage =
      signalState === "SIGNAL_LOST" && nowState !== "OFFLINE"
        ? tx("today.offline.establishing")
        : signalState === "SIGNAL_LOST"
          ? tx("today.offline.signalLost")
          : signalState === "RESTORED"
            ? tx("today.offline.linkRestored")
            : nowState === "OFFLINE"
              ? tx("today.offline.title")
              : null;
    updateHudRef.current?.({
      status: error ? "ERROR" : nowState === "OFFLINE" ? "OFFLINE" : signalState === "SIGNAL_LOST" ? "DEGRADED" : "OK",
      marqueeItems,
      statusMessage
    });
  }, [activeSlot, archivedIssue, displayIssue, error, nowSlotId, nowState, signalState, slots, tx]);

  if (error && nowState !== "OFFLINE" && !displayIssue) {
    return <BSOD message={`${tx("system.errors.todayLoad")}: ${error}`} />;
  }

  const debugPanel = debugPanelEnabled ? (
    <div className="hud-border rounded-card bg-panel-900/70 p-4 text-[0.72rem] uppercase tracking-[0.2em] text-clinical-white/60">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <span>{tx("today.debug.label")}</span>
        <span className="font-mono text-xs text-signal-accent">
          {debugTime ? `${tx("today.debug.active")} ${debugTime}` : tx("today.debug.realTime")}
        </span>
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        <button
          type="button"
          className="ui-button border-panel-700/70 text-clinical-white/70 hover:border-signal-accent/60"
          onClick={() => setDebugClock(7, 59)}
        >
          {tx("today.debug.offline")}
        </button>
        <button
          type="button"
          className="ui-button border-panel-700/70 text-clinical-white/70 hover:border-signal-accent/60"
          onClick={() => setDebugClock(8, 0)}
        >
          {tx("today.debug.slot0800")}
        </button>
        <button
          type="button"
          className="ui-button border-panel-700/70 text-clinical-white/70 hover:border-signal-accent/60"
          onClick={() => setDebugClock(12, 30)}
        >
          {tx("today.debug.slot1230")}
        </button>
        <button
          type="button"
          className="ui-button border-panel-700/70 text-clinical-white/70 hover:border-signal-accent/60"
          onClick={() => setDebugClock(16, 0)}
        >
          {tx("today.debug.slot1600")}
        </button>
        <button
          type="button"
          className="ui-button border-panel-700/70 text-clinical-white/70 hover:border-signal-accent/60"
          onClick={() => setDebugClock(20, 0)}
        >
          {tx("today.debug.transition2000")}
        </button>
        <button
          type="button"
          className="ui-button border-alert-red/60 text-alert-red hover:border-alert-red"
          onClick={clearDebug}
        >
          {tx("today.debug.clear")}
        </button>
        <button
          type="button"
          onClick={enterAmbient}
          data-testid="ambient-toggle"
          className="ui-button border-panel-700/70 text-clinical-white/70 hover:border-signal-accent/60"
        >
          {tx("today.ambientEnter")}
        </button>
      </div>
    </div>
  ) : null;

  if (nowState === "OFFLINE") {
    return (
      <section className="relative flex flex-col gap-8">
        {transitionActive && <div className="transition-overlay" aria-hidden="true" />}
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="ambient-fade flex flex-col gap-2">
            <p className="ui-kicker text-clinical-white/60">{tx("today.label")}</p>
            <h1 className="text-3xl font-semibold uppercase tracking-tightish text-alert-red">
              {tx("today.offline.title")}
            </h1>
            <p className="font-mono text-sm text-clinical-white/60">{tx("today.offline.nextBoot")}</p>
          </div>
          <div className="ambient-fade flex flex-wrap items-center gap-3">
            <p className="max-w-sm font-mono text-xs uppercase tracking-[0.22em] text-clinical-white/45">
              {tx("today.offline.archiveViaHud")}
            </p>
          </div>
        </div>
        {debugPanel}
        <div className="hud-border rounded-card bg-panel-900/60 p-6">
          <p className="text-xs uppercase tracking-[0.3em] text-clinical-white/50">
            {tx("today.offline.archivedHint")}
          </p>
          <div className="relative mt-6">
            <span className="archived-watermark">{tx("today.offline.archivedLabel")}</span>
            {archivedIssue ? (
              <div
                role="group"
                aria-disabled="true"
                onClick={triggerLockedFeedback}
                className={`offline-locked-panel ${lockedFeedback ? "is-locked-feedback" : ""}`}
              >
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
                <p className="mt-4 font-mono text-xs uppercase tracking-[0.26em] text-clinical-white/45">
                  {lockedFeedback ? tx("today.offline.lockedFeedback") : tx("today.offline.lockedHint")}
                </p>
              </div>
            ) : (
              <div className="hud-border rounded-card bg-panel-900/60 p-6 font-mono text-sm text-clinical-white/60">
                {archivedError ? tx("today.offline.noSignal") : tx("today.loading")}
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
      <div className="section-toolbar flex flex-wrap items-start justify-between gap-4">
        <div className="ambient-fade flex flex-col gap-2">
          <p className="ui-kicker text-clinical-white/60">{tx("today.label")}</p>
          <h1 className="text-3xl font-semibold uppercase tracking-tightish">{headerText}</h1>
          <p className="font-mono text-sm text-clinical-white/60">{tx("today.intro")}</p>
          {signalState === "SIGNAL_LOST" ? (
            <p className="mt-2 text-xs uppercase tracking-[0.35em] text-alert-red">
              {tx("today.offline.signalLost")}
            </p>
          ) : null}
          {signalState === "RESTORED" ? (
            <p className="mt-2 text-xs uppercase tracking-[0.35em] text-signal-accent">
              {tx("today.offline.linkRestored")}
            </p>
          ) : null}
        </div>
        <div className="ambient-fade flex flex-wrap items-center gap-3">
          {showNowAvailable && (
            <span className="rounded-full border border-alert-red/60 px-3 py-2 text-[10px] uppercase tracking-[0.3em] text-alert-red">
              {tx("today.nowAvailable")}
            </span>
          )}
          {showReturnToNow && (
            <button
              type="button"
              onClick={returnToNow}
              className="ui-button border-signal-accent/60 text-signal-accent hover:border-signal-accent hover:text-signal-accent/90"
            >
              {tx("today.returnToNow")}
            </button>
          )}
          <button
            type="button"
            onClick={openShare}
            disabled={!displayIssue || nowSlotId === null}
            data-testid="share-card-toggle"
            className="share-card-primary-button ui-button disabled:cursor-not-allowed disabled:border-panel-700/40 disabled:text-clinical-white/40"
          >
            {tx("share.button")}
          </button>
        </div>
      </div>

      {debugPanel}

      {displayIssue ? (
        <LayoutGroup>
          <div className="today-layout grid gap-6 lg:grid-cols-[minmax(13rem,15.5rem)_1fr]">
            <aside className="ambient-fade hud-border rounded-card bg-panel-900/70 p-4 sm:p-5">
              <p className="text-sm uppercase tracking-[0.25em] text-clinical-white/60">
                {tx("today.timeline.title")}
              </p>
              <div className="timeline-list mt-5 flex flex-col gap-4">
                {slots.map((slot) => {
                  const isActive = slot.slot_id === (activeSlot?.slot_id ?? slot.slot_id);
                  const thumbPick = slot.picks[0];
                  const isLocked = nowSlotId !== null ? slot.slot_id > nowSlotId : true;
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
                      disabled={isLocked}
                      onClick={() => selectSlot(slot.slot_id)}
                      className={`timeline-button flex w-full items-center gap-4 rounded-card border px-4 py-4 text-left transition ${
                        isActive
                          ? "border-signal-accent/70 bg-panel-800/70 text-signal-accent"
                          : isLocked
                            ? "border-panel-800/70 text-clinical-white/30"
                            : "border-panel-700/70 text-clinical-white/70 hover:border-clinical-white/60"
                      }`}
                    >
                      <div className="h-14 w-14 overflow-hidden rounded-md border border-panel-700/60 bg-panel-800">
                        {isLocked ? (
                          <div className="flex h-full w-full items-center justify-center font-mono text-lg text-clinical-white/50">
                            ?
                          </div>
                        ) : thumbUrl ? (
                          <img src={thumbUrl} alt="" className="h-full w-full object-cover" />
                        ) : (
                          <div className="flex h-full w-full items-center justify-center text-[8px] uppercase tracking-[0.3em] text-clinical-white/30">
                            {tx("today.timeline.thumb")}
                          </div>
                        )}
                      </div>
                      <div className="flex flex-1 flex-col gap-1">
                        <span className="text-xs uppercase tracking-[0.3em]">{slot.window_label}</span>
                        {!isLocked ? (
                          <span className="text-[11px] uppercase tracking-[0.2em] text-clinical-white/50">
                            {slot.theme}
                          </span>
                        ) : null}
                      </div>
                      {isLocked ? (
                        <span className="text-[10px] uppercase tracking-[0.3em] text-clinical-white/30">
                          {tx("today.timeline.locked")}
                        </span>
                      ) : null}
                    </button>
                  );
                })}
              </div>
              {signalState === "SIGNAL_LOST" && nowState !== "OFFLINE" ? (
                <div className="mt-6 rounded-card border border-alert-red/40 bg-panel-900/80 p-4 text-[10px] uppercase tracking-[0.3em] text-alert-red">
                  <p>{tx("today.offline.establishing")}</p>
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
                    onClick={retryNow}
                    className="mt-3 rounded-full border border-alert-red/60 px-3 py-2 text-[10px] uppercase tracking-[0.25em] text-alert-red"
                  >
                    {tx("today.offline.retry")}
                  </button>
                </div>
              ) : null}
            </aside>
            <motion.div
              className={`album-grid grid gap-4 md:grid-cols-3 xl:gap-5 ${FLAGS.dominantViewport ? "md:min-h-[68vh]" : ""}`}
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
          {tx("today.loading")}
        </div>
      )}
      {ambientActive ? <AmbientOverlay onExit={exitAmbient} /> : null}
      <ShareCardDialog
        open={shareOpen}
        issue={displayIssue}
        nowSlotId={nowSlotId}
        visualTheme={visualTheme}
        onClose={closeShare}
      />
    </section>
  );
}
