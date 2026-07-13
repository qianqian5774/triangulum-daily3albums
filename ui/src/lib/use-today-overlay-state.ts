import type { KeyboardEvent, MouseEvent } from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import { FLAGS } from "../config/flags";
import type { PickItem } from "./types";

const AMBIENT_IDLE_DELAY_MS = 120000;
const IDLE_ACTIVITY_THROTTLE_MS = 750;

export type TodayPresentationPick = PickItem & { stableId: string };

export function useTodayOverlayState({
  picks,
  prefersReducedMotion
}: {
  picks: TodayPresentationPick[];
  prefersReducedMotion: boolean | null;
}) {
  const [focusedId, setFocusedId] = useState<string | null>(null);
  const [direction, setDirection] = useState<-1 | 1>(1);
  const [glitchActive, setGlitchActive] = useState(false);
  const [ambientActive, setAmbientActive] = useState(false);
  const [shareOpen, setShareOpen] = useState(false);
  const [lockedFeedback, setLockedFeedback] = useState(false);

  const lastActiveRef = useRef<HTMLElement | null>(null);
  const glitchTimeoutRef = useRef<number | null>(null);
  const idleTimeoutRef = useRef<number | null>(null);
  const lastFocusedRef = useRef<string | null>(null);
  const lockedFeedbackTimeoutRef = useRef<number | null>(null);
  const lastIdleResetAtRef = useRef(0);

  const activeIndex = focusedId
    ? Math.max(0, picks.findIndex((pick) => pick.stableId === focusedId))
    : 0;

  const triggerGlitch = useCallback(
    (duration: number) => {
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
    },
    [prefersReducedMotion]
  );

  const openPick = useCallback(
    (pickId: string) => {
      if (!picks.some((pick) => pick.stableId === pickId)) {
        return;
      }
      setFocusedId(pickId);
    },
    [picks]
  );

  const handleOpen = useCallback(
    (pickId: string, event: MouseEvent<HTMLElement> | KeyboardEvent<HTMLElement>) => {
      lastActiveRef.current = event.currentTarget as HTMLElement;
      setDirection(1);
      openPick(pickId);
    },
    [openPick]
  );

  const handleClose = useCallback(() => {
    setFocusedId(null);
    setGlitchActive(false);
    if (glitchTimeoutRef.current) {
      window.clearTimeout(glitchTimeoutRef.current);
      glitchTimeoutRef.current = null;
    }
    window.requestAnimationFrame(() => lastActiveRef.current?.focus());
  }, []);

  const handleNext = useCallback(() => {
    if (!picks.length) return;
    const nextIndex = (activeIndex + 1) % picks.length;
    setDirection(1);
    openPick(picks[nextIndex].stableId);
    triggerGlitch(80);
  }, [activeIndex, openPick, picks, triggerGlitch]);

  const handlePrev = useCallback(() => {
    if (!picks.length) return;
    const nextIndex = (activeIndex - 1 + picks.length) % picks.length;
    setDirection(-1);
    openPick(picks[nextIndex].stableId);
    triggerGlitch(80);
  }, [activeIndex, openPick, picks, triggerGlitch]);

  const enterAmbient = useCallback(() => {
    if (idleTimeoutRef.current) {
      window.clearTimeout(idleTimeoutRef.current);
      idleTimeoutRef.current = null;
    }
    setAmbientActive(true);
  }, []);

  const exitAmbient = useCallback(() => setAmbientActive(false), []);
  const openShare = useCallback(() => setShareOpen(true), []);
  const closeShare = useCallback(() => setShareOpen(false), []);

  const triggerLockedFeedback = useCallback(() => {
    if (lockedFeedbackTimeoutRef.current) {
      window.clearTimeout(lockedFeedbackTimeoutRef.current);
    }
    setLockedFeedback(true);
    triggerGlitch(140);
    lockedFeedbackTimeoutRef.current = window.setTimeout(() => {
      setLockedFeedback(false);
      lockedFeedbackTimeoutRef.current = null;
    }, 1800);
  }, [triggerGlitch]);

  useEffect(() => {
    if (!focusedId || lastFocusedRef.current) {
      lastFocusedRef.current = focusedId;
      return;
    }
    triggerGlitch(120);
    lastFocusedRef.current = focusedId;
  }, [focusedId, triggerGlitch]);

  useEffect(
    () => () => {
      if (glitchTimeoutRef.current) {
        window.clearTimeout(glitchTimeoutRef.current);
      }
      if (lockedFeedbackTimeoutRef.current) {
        window.clearTimeout(lockedFeedbackTimeoutRef.current);
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

  const resetIdleTimer = useCallback(
    (force = false) => {
      if (focusedId || ambientActive) {
        return;
      }
      const now = Date.now();
      if (!force && now - lastIdleResetAtRef.current < IDLE_ACTIVITY_THROTTLE_MS) {
        return;
      }
      lastIdleResetAtRef.current = now;
      if (idleTimeoutRef.current) {
        window.clearTimeout(idleTimeoutRef.current);
      }
      idleTimeoutRef.current = window.setTimeout(() => {
        setAmbientActive(true);
      }, AMBIENT_IDLE_DELAY_MS);
    },
    [ambientActive, focusedId]
  );

  useEffect(() => {
    const handleActivity = () => resetIdleTimer();
    const events = ["mousemove", "mousedown", "keydown", "touchstart", "pointerdown", "wheel"];
    events.forEach((eventName) => window.addEventListener(eventName, handleActivity, { passive: true }));
    resetIdleTimer(true);
    return () => {
      events.forEach((eventName) => window.removeEventListener(eventName, handleActivity));
      if (idleTimeoutRef.current) {
        window.clearTimeout(idleTimeoutRef.current);
      }
    };
  }, [resetIdleTimer]);

  return {
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
  };
}
