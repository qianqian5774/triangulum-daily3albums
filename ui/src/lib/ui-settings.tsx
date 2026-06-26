import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState
} from "react";
import { getCopy, type Language } from "../strings/copy";
import { t } from "../strings/t";

const LANGUAGE_KEY = "tri_ui_language";
const FONT_SCALE_KEY = "tri_ui_font_scale";
export const FONT_SCALE_TIERS = [0.96, 1.02, 1.08, 1.14, 1.2, 1.26, 1.32] as const;
export const DEFAULT_FONT_SCALE = 1.32;
const MIN_FONT_SCALE = FONT_SCALE_TIERS[0];
const MAX_FONT_SCALE = FONT_SCALE_TIERS[FONT_SCALE_TIERS.length - 1];

interface UiSettingsContextValue {
  language: Language;
  setLanguage: (language: Language) => void;
  fontScale: number;
  decreaseFont: () => void;
  increaseFont: () => void;
  resetFont: () => void;
}

const UiSettingsContext = createContext<UiSettingsContextValue | null>(null);

export function clampFontScale(value: number) {
  return Math.min(MAX_FONT_SCALE, Math.max(MIN_FONT_SCALE, value));
}

export function stepFontScale(current: number, direction: -1 | 1) {
  const clamped = clampFontScale(current);
  if (direction < 0) {
    return [...FONT_SCALE_TIERS].reverse().find((tier) => tier < clamped - 0.001) ?? MIN_FONT_SCALE;
  }
  return FONT_SCALE_TIERS.find((tier) => tier > clamped + 0.001) ?? MAX_FONT_SCALE;
}

function readLanguage(): Language {
  if (typeof window === "undefined") {
    return "en";
  }
  const stored = window.localStorage.getItem(LANGUAGE_KEY);
  return stored === "zh" || stored === "en" ? stored : "en";
}

function readFontScale() {
  if (typeof window === "undefined") {
    return DEFAULT_FONT_SCALE;
  }
  const stored = Number(window.localStorage.getItem(FONT_SCALE_KEY));
  return Number.isFinite(stored) ? clampFontScale(stored) : DEFAULT_FONT_SCALE;
}

export function UiSettingsProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>(() => readLanguage());
  const [fontScale, setFontScale] = useState(() => readFontScale());

  useEffect(() => {
    if (typeof document === "undefined") {
      return;
    }
    document.documentElement.style.setProperty("--ui-font-scale", fontScale.toFixed(2));
    document.documentElement.lang = language === "zh" ? "zh-CN" : "en";
  }, [fontScale, language]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    window.localStorage.setItem(LANGUAGE_KEY, language);
  }, [language]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    window.localStorage.setItem(FONT_SCALE_KEY, fontScale.toFixed(2));
  }, [fontScale]);

  const setLanguage = useCallback((next: Language) => {
    setLanguageState(next);
  }, []);

  const decreaseFont = useCallback(() => {
    setFontScale((current) => stepFontScale(current, -1));
  }, []);

  const increaseFont = useCallback(() => {
    setFontScale((current) => stepFontScale(current, 1));
  }, []);

  const resetFont = useCallback(() => {
    setFontScale(DEFAULT_FONT_SCALE);
  }, []);

  const value = useMemo(
    () => ({ language, setLanguage, fontScale, decreaseFont, increaseFont, resetFont }),
    [decreaseFont, fontScale, increaseFont, language, resetFont, setLanguage]
  );

  return <UiSettingsContext.Provider value={value}>{children}</UiSettingsContext.Provider>;
}

export function useUiSettings() {
  const value = useContext(UiSettingsContext);
  if (!value) {
    throw new Error("useUiSettings must be used inside UiSettingsProvider");
  }
  return value;
}

export function useT() {
  const { language } = useUiSettings();
  return useCallback((key: string) => t(key, language), [language]);
}

export function useLocalizedCopy() {
  const { language } = useUiSettings();
  return getCopy(language);
}
