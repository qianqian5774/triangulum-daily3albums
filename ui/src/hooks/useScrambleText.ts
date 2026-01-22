import { useEffect, useMemo, useState } from "react";
import { useReducedMotion } from "framer-motion";

const SCRAMBLE_CHARS = "#@!$%&*+=?";

export function useScrambleText(text: string) {
  const prefersReducedMotion = useReducedMotion();
  const [displayText, setDisplayText] = useState(text);

  const characters = useMemo(() => SCRAMBLE_CHARS.split(""), []);

  useEffect(() => {
    if (prefersReducedMotion) {
      setDisplayText(text);
      return;
    }

    const totalDurationMs = 700;
    let frameId = 0;
    let start: number | null = null;

    const tick = (timestamp: number) => {
      if (start === null) {
        start = timestamp;
      }
      const elapsed = timestamp - start;
      const progress = Math.min(1, elapsed / totalDurationMs);
      const revealCount = Math.floor(progress * text.length);
      const scrambled = text
        .split("")
        .map((char, index) => (index < revealCount ? char : characters[Math.floor(Math.random() * characters.length)]))
        .join("");

      setDisplayText(scrambled);

      if (progress < 1) {
        frameId = window.requestAnimationFrame(tick);
      } else {
        setDisplayText(text);
      }
    };

    frameId = window.requestAnimationFrame(tick);

    return () => window.cancelAnimationFrame(frameId);
  }, [characters, prefersReducedMotion, text]);

  return displayText;
}
