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

    let frame = 0;
    const totalFrames = Math.max(12, text.length * 2);

    const interval = window.setInterval(() => {
      frame += 1;
      const revealCount = Math.floor((frame / totalFrames) * text.length);
      const scrambled = text
        .split("")
        .map((char, index) => (index < revealCount ? char : characters[Math.floor(Math.random() * characters.length)]))
        .join("");

      setDisplayText(scrambled);

      if (frame >= totalFrames) {
        window.clearInterval(interval);
        setDisplayText(text);
      }
    }, 30);

    return () => window.clearInterval(interval);
  }, [characters, prefersReducedMotion, text]);

  return displayText;
}
