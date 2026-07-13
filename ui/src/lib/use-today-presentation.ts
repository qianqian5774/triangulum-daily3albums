import { useCallback, useEffect, useMemo, useState } from "react";
import { getSlotWindowLabel, type NowState } from "./bjt";
import type { TodayIssue, TodaySlot } from "./types";
import type { TodayPresentationPick } from "./use-today-overlay-state";

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

export function useTodayPresentation({
  displayIssue,
  issue,
  lastGoodIssue,
  nowSlotId,
  nowState
}: {
  displayIssue: TodayIssue | null;
  issue: TodayIssue | null;
  lastGoodIssue: TodayIssue | null;
  nowSlotId: number | null;
  nowState: NowState;
}) {
  const [selectedSlotId, setSelectedSlotId] = useState<number | null>(null);
  const coverCacheKey = issue?.run_id ?? issue?.date ?? lastGoodIssue?.run_id ?? lastGoodIssue?.date ?? "";

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
        window_label: getSlotWindowLabel(0),
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

  const picks = useMemo<TodayPresentationPick[]>(() => {
    if (!displayIssue) {
      return [];
    }
    const activePicks = activeSlot?.picks ?? displayIssue.picks;
    return activePicks.map((pick) => ({
      ...pick,
      stableId: deriveStableId(pick as { title: string; artist_credit: string; slot: string; id?: string })
    }));
  }, [activeSlot, displayIssue]);

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

  const selectSlot = useCallback(
    (slotId: number) => {
      if (nowSlotId !== null && slotId > nowSlotId) {
        return;
      }
      setSelectedSlotId(slotId);
    },
    [nowSlotId]
  );

  const returnToNow = useCallback(() => setSelectedSlotId(nowSlotId), [nowSlotId]);
  const showReturnToNow =
    nowSlotId !== null && selectedSlotId !== null && selectedSlotId !== nowSlotId && nowState !== "OFFLINE";

  return {
    activeSlot,
    coverCacheKey,
    picks,
    returnToNow,
    selectSlot,
    selectedSlotId,
    setSelectedSlotId,
    showNowAvailable: showReturnToNow,
    showReturnToNow,
    slots
  };
}
