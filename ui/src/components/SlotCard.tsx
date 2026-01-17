import { resolvePublicPath } from "../lib/paths";
import type { PickItem } from "../lib/types";

const slotStyles: Record<PickItem["slot"], string> = {
  Headliner: "border-acid-green/60 text-acid-green",
  Lineage: "border-clinical-white/40 text-clinical-white",
  DeepCut: "border-alert-red/60 text-alert-red"
};

const slotLabels: Record<PickItem["slot"], string> = {
  Headliner: "Headliner",
  Lineage: "Lineage",
  DeepCut: "Deep Cut"
};

interface SlotCardProps {
  pick: PickItem;
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

export function SlotCard({ pick }: SlotCardProps) {
  const coverUrl = resolveCover(pick.cover.optimized_cover_url);
  return (
    <article className="hud-border flex h-full flex-col overflow-hidden rounded-card bg-panel-800/70">
      <div className="relative aspect-square w-full overflow-hidden bg-panel-900">
        {coverUrl ? (
          <img
            src={coverUrl}
            alt={`${pick.title} cover`}
            className="h-full w-full object-cover"
            loading="lazy"
          />
        ) : (
          <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-panel-900 via-panel-700 to-panel-900">
            <span className="font-mono text-xs uppercase tracking-[0.4em] text-clinical-white/40">No Cover</span>
          </div>
        )}
        <div className="absolute left-4 top-4">
          <span
            className={`rounded-full border px-3 py-1 text-[10px] uppercase tracking-[0.3em] ${
              slotStyles[pick.slot]
            }`}
          >
            {slotLabels[pick.slot]}
          </span>
        </div>
      </div>
      <div className="flex flex-1 flex-col gap-3 px-5 py-4">
        <div>
          <h3 className="glitch-text text-lg font-semibold uppercase tracking-tightish">{pick.title}</h3>
          <p className="text-sm text-clinical-white/80">{pick.artist_credit || "Unknown Artist"}</p>
        </div>
        <div className="flex flex-wrap gap-2 text-xs uppercase tracking-[0.2em] text-clinical-white/60">
          {pick.first_release_year && <span>{pick.first_release_year}</span>}
          {pick.tags?.[0]?.name && <span>#{pick.tags[0].name}</span>}
        </div>
        <div className="mt-auto flex flex-wrap gap-2 text-xs text-clinical-white/70">
          {pick.links?.musicbrainz && (
            <a className="underline decoration-acid-green/60 underline-offset-4" href={pick.links.musicbrainz}>
              MusicBrainz
            </a>
          )}
          {pick.links?.youtube_search && (
            <a className="underline decoration-clinical-white/40 underline-offset-4" href={pick.links.youtube_search}>
              YouTube
            </a>
          )}
        </div>
      </div>
    </article>
  );
}
