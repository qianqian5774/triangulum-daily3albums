import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { type TouchEvent, useEffect, useMemo, useRef, useState } from "react";
import { useScrambleText } from "../hooks/useScrambleText";
import { resolveCoverUrl } from "../lib/covers";
import { useT } from "../lib/ui-settings";
import type { PickItem } from "../lib/types";

export interface TreatmentPick extends PickItem {
  stableId: string;
}

interface TreatmentViewerOverlayProps {
  picks: TreatmentPick[];
  activeId: string;
  direction: -1 | 1;
  onClose: () => void;
  onNext: () => void;
  onPrev: () => void;
  glitchActive?: boolean;
  cacheKey?: string;
}

export function TreatmentViewerOverlay({
  picks,
  activeId,
  direction,
  onClose,
  onNext,
  onPrev,
  glitchActive,
  cacheKey
}: TreatmentViewerOverlayProps) {
  const tx = useT();
  const prefersReducedMotion = useReducedMotion();
  const touchStartXRef = useRef<number | null>(null);
  const [retryToken, setRetryToken] = useState<string | null>(null);
  const [coverFailed, setCoverFailed] = useState(false);

  const activePick = useMemo(
    () => picks.find((pick) => pick.stableId === activeId) ?? picks[0],
    [activeId, picks]
  );
  const [coverReady, setCoverReady] = useState(false);
  const debugEnabled = useMemo(() => {
    if (typeof window === "undefined") {
      return false;
    }
    const params = new URLSearchParams(window.location.search);
    if (params.get("debug") === "1") {
      return true;
    }
    try {
      return window.localStorage.getItem("tri_debug") === "1";
    } catch {
      return false;
    }
  }, []);

  useEffect(() => {
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
      }
      if (event.key === "ArrowRight") {
        event.preventDefault();
        onNext();
      }
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        onPrev();
      }
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [onClose, onNext, onPrev]);

  if (!activePick) {
    return null;
  }

  const coverVersionKey = activePick.cover.cover_version ?? cacheKey;
  const coverUrl = resolveCoverUrl(activePick.cover.optimized_cover_url, coverVersionKey, retryToken);
  const scrambledTitle = useScrambleText(activePick.title);
  const displayCover = !coverFailed && coverUrl;

  const handleTouchStart = (event: TouchEvent<HTMLElement>) => {
    touchStartXRef.current = event.touches[0]?.clientX ?? null;
  };

  const handleTouchEnd = (event: TouchEvent<HTMLElement>) => {
    const startX = touchStartXRef.current;
    touchStartXRef.current = null;
    if (startX === null) {
      return;
    }
    const endX = event.changedTouches[0]?.clientX ?? startX;
    const delta = endX - startX;
    if (Math.abs(delta) < 48) {
      return;
    }
    if (delta < 0) {
      onNext();
      return;
    }
    onPrev();
  };

  useEffect(() => {
    setRetryToken(null);
    setCoverFailed(false);
  }, [activePick.stableId, cacheKey]);

  useEffect(() => {
    let active = true;
    setCoverReady(false);
    if (!displayCover) {
      setCoverReady(true);
      return () => {
        active = false;
      };
    }
    const image = new Image();
    const finish = () => {
      if (!active) return;
      setCoverReady(true);
    };
    image.onload = finish;
    image.onerror = () => {
      if (!active) return;
      if (retryToken === null) {
        setRetryToken(Date.now().toString());
        return;
      }
      setCoverFailed(true);
      setCoverReady(true);
    };
    image.src = displayCover;
    if (image.decode) {
      image.decode().then(finish).catch(finish);
    }
    return () => {
      active = false;
    };
  }, [displayCover, retryToken]);

  const parentVariants = prefersReducedMotion
    ? {
        initial: { opacity: 0 },
        animate: { opacity: 1 },
        exit: { opacity: 0 }
      }
    : {
        initial: { opacity: 0, x: direction > 0 ? 24 : -24 },
        animate: {
          opacity: 1,
          x: 0,
          transition: { staggerChildren: 0.1, delayChildren: 0.05 }
        },
        exit: { opacity: 0, x: direction > 0 ? -24 : 24 }
      };

  const childVariants = prefersReducedMotion
    ? {
        initial: { opacity: 0 },
        animate: { opacity: 1 },
        exit: { opacity: 0 }
      }
    : {
        initial: { opacity: 0, y: 12 },
        animate: { opacity: 1, y: 0, transition: { duration: 0.25 } },
        exit: { opacity: 0, y: -8, transition: { duration: 0.2 } }
      };

  return (
    <AnimatePresence>
      <motion.div
        className="fixed inset-0 z-[70] flex items-center justify-center bg-void-black/84 backdrop-blur-xl"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        aria-hidden="true"
      />
      <motion.div
        className="fixed inset-0 z-[80] flex items-center justify-center px-3 py-4 sm:px-4 sm:py-6"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
      >
        <motion.div
          layoutId={`card-${activePick.stableId}`}
          className={`viewer-dialog relative w-full max-w-5xl overflow-hidden rounded-card border border-panel-700/80 bg-panel-900/95 shadow-hard-xl ${
            glitchActive ? "glitch-flash" : ""
          }`}
          role="dialog"
          aria-modal="true"
          aria-label={activePick.title}
          data-testid="treatment-overlay"
          onClick={(event) => event.stopPropagation()}
          onTouchStart={handleTouchStart}
          onTouchEnd={handleTouchEnd}
        >
          <AnimatePresence mode="wait">
            <motion.div
              key={activePick.stableId}
              className="viewer-content relative z-30 grid gap-5 p-4 sm:p-5 md:grid-cols-[44%_1fr] md:items-stretch md:gap-7 md:p-6"
              variants={parentVariants}
              initial="initial"
              animate="animate"
              exit="exit"
            >
              <motion.div className="w-full" variants={childVariants}>
                <div className="relative mx-auto aspect-square w-full max-w-[34rem] overflow-hidden rounded-card bg-panel-800">
                  <div className="absolute inset-0 bg-gradient-to-br from-panel-900 via-panel-800 to-panel-900" />
                  {displayCover ? (
                    <motion.img
                      layoutId={`cover-${activePick.stableId}`}
                      src={displayCover}
                      alt={`${activePick.title} cover`}
                      className={`relative z-10 h-full w-full object-cover transition-opacity duration-200 ${
                        coverReady ? "opacity-100" : "opacity-0"
                      }`}
                    />
                  ) : (
                    <div className="relative z-10 flex h-full w-full items-center justify-center bg-gradient-to-br from-panel-900 via-panel-700 to-panel-900">
                      <span className="font-mono text-xs uppercase tracking-[0.4em] text-clinical-white/40">
                        {tx("treatment.cover.missing")}
                      </span>
                    </div>
                  )}
                </div>
              </motion.div>
              <motion.div className="viewer-detail-panel flex min-h-0 flex-col gap-5 md:col-start-2" variants={childVariants}>
                <div className="flex items-start justify-between gap-4">
                  <div className="pt-1">
                    <p className="ui-kicker text-clinical-white/50">
                      {tx("treatment.viewer.enter")}
                    </p>
                    <h2 className="glow-text mt-2 text-2xl font-semibold uppercase tracking-tightish sm:text-3xl">
                      {scrambledTitle}
                    </h2>
                    <p className="text-base text-clinical-white/70">
                      {activePick.artist_credit || tx("treatment.cover.unknownArtist")}
                    </p>
                    <p className="mt-4 text-xs uppercase tracking-[0.2em] text-clinical-white/60">
                      {activePick.first_release_year && <span>{activePick.first_release_year}</span>}
                      {activePick.tags?.[0]?.name && (
                        <span className="ml-3">#{activePick.tags[0].name}</span>
                      )}
                      <span className="ml-3">{tx(`treatment.slot.${activePick.slot}`)}</span>
                    </p>
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-3 text-sm text-clinical-white/70">
                  {activePick.links?.musicbrainz && (
                    <a
                      className="inline-flex min-h-[36px] items-center px-2 py-1 text-[11px] uppercase tracking-[0.3em] text-acid-green underline decoration-acid-green/60 underline-offset-4 transition hover:text-acid-green/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-acid-green/70"
                      href={activePick.links.musicbrainz}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {tx("treatment.links.musicbrainz")}
                    </a>
                  )}
                  {activePick.links?.youtube_search && (
                    <a
                      className="inline-flex min-h-[36px] items-center px-2 py-1 text-[11px] uppercase tracking-[0.3em] text-clinical-white underline decoration-clinical-white/50 underline-offset-4 transition hover:text-clinical-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-clinical-white/60"
                      href={activePick.links.youtube_search}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {tx("treatment.links.youtube")}
                    </a>
                  )}
                </div>
                <div className="viewer-actions mt-auto flex flex-col items-end gap-3 text-right">
                  <div className="flex flex-wrap justify-end gap-3">
                    <button
                      type="button"
                      onClick={onPrev}
                      className="ui-button border-panel-700/80 text-clinical-white/70 hover:border-acid-green/60 hover:text-acid-green"
                    >
                      {tx("treatment.viewer.prev")}
                    </button>
                    <button
                      type="button"
                      onClick={onNext}
                      className="ui-button border-panel-700/80 text-clinical-white/70 hover:border-acid-green/60 hover:text-acid-green"
                    >
                      {tx("treatment.viewer.next")}
                    </button>
                  </div>
                  {debugEnabled && activePick.reason && (
                    // Diagnostic output is intentionally hidden unless ?debug=1 or localStorage tri_debug=1.
                    <p className="text-[10px] font-mono text-clinical-white/50">
                      Diagnostic: {activePick.reason}
                    </p>
                  )}
                </div>
              </motion.div>
            </motion.div>
          </AnimatePresence>
          <button
            type="button"
            onClick={onPrev}
            className="viewer-click-zone viewer-click-zone-left"
            aria-label={tx("treatment.viewer.prev")}
          />
          <button
            type="button"
            onClick={onNext}
            className="viewer-click-zone viewer-click-zone-right"
            aria-label={tx("treatment.viewer.next")}
          />
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
