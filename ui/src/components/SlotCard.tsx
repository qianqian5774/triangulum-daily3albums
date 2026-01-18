import type { KeyboardEvent, MouseEvent } from "react";
import { motion } from "framer-motion";
import { resolvePublicPath } from "../lib/paths";
import { t } from "../strings/t";
import type { PickItem } from "../lib/types";

const slotStyles: Record<PickItem["slot"], string> = {
  Headliner: "border-acid-green/60 text-acid-green",
  Lineage: "border-clinical-white/40 text-clinical-white",
  DeepCut: "border-alert-red/60 text-alert-red"
};

interface SlotCardProps {
  pick: PickItem;
  onSelect?: (event: MouseEvent<HTMLElement> | KeyboardEvent<HTMLElement>) => void;
  layoutId?: string;
  dataTestId?: string;
  className?: string;
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

export function SlotCard({ pick, onSelect, layoutId, dataTestId, className }: SlotCardProps) {
  const coverUrl = resolveCover(pick.cover.optimized_cover_url);
  const isInteractive = Boolean(onSelect);

  const handleKeyDown = (event: KeyboardEvent<HTMLElement>) => {
    if (!onSelect) {
      return;
    }
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onSelect(event);
    }
  };

  return (
    <motion.article
      layoutId={layoutId}
      data-testid={dataTestId}
      onClick={onSelect}
      onKeyDown={handleKeyDown}
      role={isInteractive ? "button" : undefined}
      tabIndex={isInteractive ? 0 : undefined}
      aria-label={isInteractive ? t("treatment.viewer.enter") : undefined}
      className={`hud-border flex h-full flex-col overflow-hidden rounded-card bg-panel-800/70 transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-acid ${
        isInteractive ? "cursor-pointer hover:border-acid-green/50" : ""
      } ${className ?? ""}`}
    >
      <div className="relative aspect-square w-full overflow-hidden bg-panel-900">
        {coverUrl ? (
          <img src={coverUrl} alt={`${pick.title} cover`} className="h-full w-full object-cover" loading="lazy" />
        ) : (
          <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-panel-900 via-panel-700 to-panel-900">
            <span className="font-mono text-xs uppercase tracking-[0.4em] text-clinical-white/40">
              {t("treatment.cover.missing")}
            </span>
          </div>
        )}
        <div className="absolute left-4 top-4">
          <span
            className={`rounded-full border px-3 py-1 text-[10px] uppercase tracking-[0.3em] ${slotStyles[pick.slot]}`}
          >
            {t(`treatment.slot.${pick.slot}`)}
          </span>
        </div>
      </div>
      <div className="flex flex-1 flex-col gap-3 px-5 py-4">
        <div>
          <h3 className="glitch-text text-lg font-semibold uppercase tracking-tightish">{pick.title}</h3>
          <p className="text-sm text-clinical-white/80">
            {pick.artist_credit || t("treatment.cover.unknownArtist")}
          </p>
        </div>
        <div className="flex flex-wrap gap-2 text-xs uppercase tracking-[0.2em] text-clinical-white/60">
          {pick.first_release_year && <span>{pick.first_release_year}</span>}
          {pick.tags?.[0]?.name && <span>#{pick.tags[0].name}</span>}
        </div>
        <div className="mt-auto flex flex-wrap gap-2 text-xs text-clinical-white/70">
          {pick.links?.musicbrainz && (
            <a
              className="underline decoration-acid-green/60 underline-offset-4"
              href={pick.links.musicbrainz}
              onClick={(event) => event.stopPropagation()}
              target="_blank"
              rel="noreferrer"
            >
              {t("treatment.links.musicbrainz")}
            </a>
          )}
          {pick.links?.youtube_search && (
            <a
              className="underline decoration-clinical-white/40 underline-offset-4"
              href={pick.links.youtube_search}
              onClick={(event) => event.stopPropagation()}
              target="_blank"
              rel="noreferrer"
            >
              {t("treatment.links.youtube")}
            </a>
          )}
        </div>
      </div>
    </motion.article>
  );
}
