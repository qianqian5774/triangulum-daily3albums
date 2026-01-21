import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useEffect, useMemo, useRef } from "react";
import { useScrambleText } from "../hooks/useScrambleText";
import { appendCacheBuster, resolvePublicPath } from "../lib/paths";
import { t } from "../strings/t";
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

function resolveCover(url: string, cacheKey?: string) {
  const trimmed = url.trim();
  if (!trimmed) {
    return null;
  }
  if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
    return appendCacheBuster(trimmed, cacheKey);
  }
  const safe = trimmed.replace(/^\//, "");
  return appendCacheBuster(resolvePublicPath(safe), cacheKey);
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
  const prefersReducedMotion = useReducedMotion();
  const closeRef = useRef<HTMLButtonElement | null>(null);

  const activePick = useMemo(
    () => picks.find((pick) => pick.stableId === activeId) ?? picks[0],
    [activeId, picks]
  );
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
    closeRef.current?.focus();
  }, [activeId]);

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
  const coverUrl = resolveCover(activePick.cover.optimized_cover_url, coverVersionKey);
  const scrambledTitle = useScrambleText(activePick.title);

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
        className="fixed inset-0 z-40 flex items-center justify-center bg-void-black/80 backdrop-blur-xl"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        aria-hidden="true"
      />
      <motion.div
        className="fixed inset-0 z-50 flex items-center justify-center px-4 py-6"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
      >
        <motion.div
          layoutId={`card-${activePick.stableId}`}
          className={`relative w-full max-w-5xl overflow-hidden rounded-card border border-panel-700/80 bg-panel-900/95 shadow-hard-xl ${
            glitchActive ? "glitch-flash" : ""
          }`}
          role="dialog"
          aria-modal="true"
          aria-label={activePick.title}
          data-testid="treatment-overlay"
          onClick={(event) => event.stopPropagation()}
        >
          <AnimatePresence mode="wait">
            <motion.div
              key={activePick.stableId}
              className="relative z-10 grid gap-6 p-6 md:grid-cols-[45%_1fr] md:items-start"
              variants={parentVariants}
              initial="initial"
              animate="animate"
              exit="exit"
            >
              <motion.div
                className="w-full"
                variants={childVariants}
                layoutId={`cover-${activePick.stableId}`}
              >
                <div className="relative aspect-square w-full overflow-hidden rounded-card bg-panel-800">
                  {coverUrl ? (
                    <img src={coverUrl} alt={`${activePick.title} cover`} className="h-full w-full object-cover" />
                  ) : (
                    <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-panel-900 via-panel-700 to-panel-900">
                      <span className="font-mono text-xs uppercase tracking-[0.4em] text-clinical-white/40">
                        {t("treatment.cover.missing")}
                      </span>
                    </div>
                  )}
                </div>
              </motion.div>
              <motion.div
                className="flex items-start justify-between gap-4 md:col-start-2"
                variants={childVariants}
              >
                <div>
                  <p className="text-xs uppercase tracking-[0.3em] text-clinical-white/50">
                    {t("treatment.viewer.enter")}
                  </p>
                  <h2 className="glow-text mt-2 text-2xl font-semibold uppercase tracking-tightish">
                    {scrambledTitle}
                  </h2>
                  <p className="text-sm text-clinical-white/70">
                    {activePick.artist_credit || t("treatment.cover.unknownArtist")}
                  </p>
                </div>
                <button
                  ref={closeRef}
                  type="button"
                  onClick={onClose}
                  className="rounded-full border border-panel-700/80 px-4 py-2 text-xs uppercase tracking-[0.3em] text-clinical-white/70 transition hover:border-acid-green/60 hover:text-acid-green"
                >
                  {t("treatment.viewer.exit")}
                </button>
              </motion.div>
              <motion.div
                className="flex flex-wrap gap-3 text-xs uppercase tracking-[0.2em] text-clinical-white/60 md:col-start-2"
                variants={childVariants}
              >
                {activePick.first_release_year && <span>{activePick.first_release_year}</span>}
                {activePick.tags?.[0]?.name && <span>#{activePick.tags[0].name}</span>}
                <span>{t(`treatment.slot.${activePick.slot}`)}</span>
              </motion.div>
              <div className="mt-auto flex flex-col gap-4 md:col-start-2">
                <div className="flex flex-wrap items-center gap-3 text-sm text-clinical-white/70">
                  {activePick.links?.musicbrainz && (
                    <a
                      className="inline-flex min-h-[44px] items-center rounded-full border border-acid-green/30 px-4 py-2 uppercase tracking-[0.2em] text-acid-green transition hover:border-acid-green/70 hover:text-acid-green/90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-acid-green/70"
                      href={activePick.links.musicbrainz}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {t("treatment.links.musicbrainz")}
                    </a>
                  )}
                  {activePick.links?.youtube_search && (
                    <a
                      className="inline-flex min-h-[44px] items-center rounded-full border border-clinical-white/30 px-4 py-2 uppercase tracking-[0.2em] text-clinical-white transition hover:border-clinical-white/70 hover:text-clinical-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-clinical-white/60"
                      href={activePick.links.youtube_search}
                      target="_blank"
                      rel="noreferrer"
                    >
                      {t("treatment.links.youtube")}
                    </a>
                  )}
                </div>
                <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                  <div className="flex flex-col gap-2">
                    <p className="text-[10px] uppercase tracking-[0.3em] text-clinical-white/40">
                      {t("treatment.viewer.instructions")}
                    </p>
                    {debugEnabled && activePick.reason && (
                      // Diagnostic output is intentionally hidden unless ?debug=1 or localStorage tri_debug=1.
                      <p className="text-[10px] font-mono text-clinical-white/50">
                        Diagnostic: {activePick.reason}
                      </p>
                    )}
                  </div>
                  <div className="flex flex-wrap gap-3">
                    <button
                      type="button"
                      onClick={onPrev}
                      className="rounded-full border border-panel-700/80 px-4 py-2 text-xs uppercase tracking-[0.3em] text-clinical-white/70 transition hover:border-acid-green/60 hover:text-acid-green focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-acid-green/70"
                    >
                      {t("treatment.viewer.prev")}
                    </button>
                    <button
                      type="button"
                      onClick={onNext}
                      className="rounded-full border border-panel-700/80 px-4 py-2 text-xs uppercase tracking-[0.3em] text-clinical-white/70 transition hover:border-acid-green/60 hover:text-acid-green focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-acid-green/70"
                    >
                      {t("treatment.viewer.next")}
                    </button>
                  </div>
                </div>
              </div>
            </motion.div>
          </AnimatePresence>
          <button
            type="button"
            onClick={onPrev}
            className="absolute inset-y-0 left-0 z-0 w-[18%] cursor-pointer"
            aria-label={t("treatment.viewer.prev")}
          />
          <button
            type="button"
            onClick={onNext}
            className="absolute inset-y-0 right-0 z-0 w-[18%] cursor-pointer"
            aria-label={t("treatment.viewer.next")}
          />
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
