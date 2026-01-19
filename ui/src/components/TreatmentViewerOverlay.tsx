import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { useEffect, useMemo, useRef } from "react";
import { useScrambleText } from "../hooks/useScrambleText";
import { resolvePublicPath } from "../lib/paths";
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
}

function resolveCover(url: string) {
  const trimmed = url.trim();
  if (!trimmed) {
    return null;
  }
  if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
    return trimmed;
  }
  const safe = trimmed.replace(/^\//, "");
  return resolvePublicPath(safe);
}

export function TreatmentViewerOverlay({
  picks,
  activeId,
  direction,
  onClose,
  onNext,
  onPrev,
  glitchActive
}: TreatmentViewerOverlayProps) {
  const prefersReducedMotion = useReducedMotion();
  const closeRef = useRef<HTMLButtonElement | null>(null);

  const activePick = useMemo(
    () => picks.find((pick) => pick.stableId === activeId) ?? picks[0],
    [activeId, picks]
  );

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

  const coverUrl = resolveCover(activePick.cover.optimized_cover_url);
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
              {activePick.reason && (
                <motion.p
                  className="text-sm text-clinical-white/75 md:col-start-2"
                  variants={childVariants}
                >
                  {activePick.reason}
                </motion.p>
              )}
              <div className="mt-auto flex flex-wrap items-center gap-3 text-xs text-clinical-white/70 md:col-start-2">
                {activePick.links?.musicbrainz && (
                  <a
                    className="underline decoration-acid-green/60 underline-offset-4"
                    href={activePick.links.musicbrainz}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {t("treatment.links.musicbrainz")}
                  </a>
                )}
                {activePick.links?.youtube_search && (
                  <a
                    className="underline decoration-clinical-white/40 underline-offset-4"
                    href={activePick.links.youtube_search}
                    target="_blank"
                    rel="noreferrer"
                  >
                    {t("treatment.links.youtube")}
                  </a>
                )}
              </div>
              <p className="text-[10px] uppercase tracking-[0.3em] text-clinical-white/40 md:col-start-2">
                {t("treatment.viewer.instructions")}
              </p>
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
          <div className="pointer-events-none absolute bottom-6 right-6 z-10 flex gap-3">
            <button
              type="button"
              onClick={onPrev}
              className="pointer-events-auto rounded-full border border-panel-700/80 px-4 py-2 text-xs uppercase tracking-[0.3em] text-clinical-white/70 transition hover:border-acid-green/60 hover:text-acid-green"
            >
              {t("treatment.viewer.prev")}
            </button>
            <button
              type="button"
              onClick={onNext}
              className="pointer-events-auto rounded-full border border-panel-700/80 px-4 py-2 text-xs uppercase tracking-[0.3em] text-clinical-white/70 transition hover:border-acid-green/60 hover:text-acid-green"
            >
              {t("treatment.viewer.next")}
            </button>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
