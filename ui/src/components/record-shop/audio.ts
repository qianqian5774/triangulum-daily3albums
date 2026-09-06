import { useCallback, useEffect, useRef, useState } from "react";

export type RecordShopCue =
  | "hover"
  | "press"
  | "view"
  | "door"
  | "threshold"
  | "arrival"
  | "device"
  | "history"
  | "record";

type Space = "exterior" | "interior";

interface AmbientVoice {
  gain: GainNode;
  sources: AudioScheduledSourceNode[];
}

const cueNotes: Record<RecordShopCue, Array<[number, number, number, OscillatorType]>> = {
  hover: [[410, 0, 0.018, "sine"]],
  press: [[160, 0, 0.035, "sine"]],
  view: [[240, 0, 0.055, "sine"]],
  door: [[142, 0, 0.065, "triangle"], [880, .12, .26, "sine"], [1320, .125, .18, "sine"]],
  threshold: [[92, 0, .09, "sine"]],
  arrival: [[118, 0, .06, "sine"]],
  device: [[430, 0, .055, "sine"], [645, .045, .08, "sine"]],
  history: [[290, 0, .045, "sine"]],
  record: [[175, 0, .028, "triangle"]]
};

function createContext() {
  const AudioContextConstructor = window.AudioContext
    ?? (window as typeof window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  return AudioContextConstructor ? new AudioContextConstructor() : null;
}

export function useRecordShopAudio(space: Space, approaching = false) {
  const ambientSpace = approaching ? "interior" : space;
  const [enabled, setEnabled] = useState(false);
  const enabledRef = useRef(false);
  const contextRef = useRef<AudioContext | null>(null);
  const ambientRef = useRef<AmbientVoice | null>(null);
  const masterRef = useRef<GainNode | null>(null);
  const lastHoverRef = useRef(0);

  const stopAmbient = useCallback((fadeSeconds = 0.2) => {
    const context = contextRef.current;
    const ambient = ambientRef.current;
    if (!context || !ambient) return;
    const now = context.currentTime;
    ambient.gain.gain.cancelScheduledValues(now);
    ambient.gain.gain.setValueAtTime(Math.max(0.0001, ambient.gain.gain.value), now);
    ambient.gain.gain.exponentialRampToValueAtTime(0.0001, now + fadeSeconds);
    ambient.sources.forEach((source) => source.stop(now + fadeSeconds + 0.03));
    ambientRef.current = null;
  }, []);

  const startAmbient = useCallback((nextSpace: Space) => {
    const context = contextRef.current;
    if (!context || context.state !== "running") return;
    stopAmbient(0.32);
    const filter = context.createBiquadFilter();
    const gain = context.createGain();
    const now = context.currentTime;
    filter.type = "lowpass";
    filter.frequency.setValueAtTime(nextSpace === "interior" ? 280 : 720, now);
    filter.Q.setValueAtTime(0.7, now);
    gain.gain.setValueAtTime(0.0001, now);
    gain.gain.exponentialRampToValueAtTime(nextSpace === "interior" ? .075 : .055, now + .85);
    filter.connect(gain).connect(masterRef.current!);
    // Soft air outside, a drier low room tone inside. No melodic loop or
    // catalogue playback; the short door bell is the principal sonic landmark.
    const buffer = context.createBuffer(1, context.sampleRate * 4, context.sampleRate);
    const samples = buffer.getChannelData(0);
    let previous = 0;
    for (let i = 0; i < samples.length; i++) {
      previous = (previous + (Math.random() * 2 - 1) * .025) / 1.025;
      samples[i] = previous * 3;
    }
    const air = context.createBufferSource(); air.buffer = buffer; air.loop = true;
    air.connect(filter); air.start(now);
    ambientRef.current = { gain, sources: [air] };
    air.onended = () => { air.disconnect(); filter.disconnect(); gain.disconnect(); };
  }, [stopAmbient]);

  const playCue = useCallback((cue: RecordShopCue) => {
    const context = contextRef.current;
    if (!enabledRef.current || !context || context.state !== "running") return;
    const now = context.currentTime;
    if (cue === "hover" && now - lastHoverRef.current < .11) return;
    if (cue === "hover") lastHoverRef.current = now;
    for (const [frequency, offset, duration, type] of cueNotes[cue]) {
      const oscillator = context.createOscillator();
      const gain = context.createGain();
      oscillator.type = type;
      oscillator.frequency.setValueAtTime(frequency, now + offset);
      gain.gain.setValueAtTime(0.0001, now + offset);
      gain.gain.exponentialRampToValueAtTime(cue === "hover" ? .003 : cue === "door" ? .018 : .012, now + offset + 0.006);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + offset + duration);
      oscillator.connect(gain).connect(masterRef.current!);
      oscillator.start(now + offset);
      oscillator.stop(now + offset + duration + 0.015);
      oscillator.onended = () => { oscillator.disconnect(); gain.disconnect(); };
    }
  }, []);

  const toggleSound = useCallback(() => {
    if (enabled) {
      enabledRef.current = false;
      masterRef.current?.gain.setTargetAtTime(0, contextRef.current!.currentTime, .025);
      stopAmbient();
      setEnabled(false);
      return;
    }
    const context = contextRef.current ?? createContext();
    if (!context) return;
    contextRef.current = context;
    if (!masterRef.current) { masterRef.current = context.createGain(); masterRef.current.connect(context.destination); }
    void context.resume().then(() => {
      if (contextRef.current !== context) return;
      enabledRef.current = true;
      masterRef.current!.gain.setTargetAtTime(1, context.currentTime, .04);
      setEnabled(true);
      const now = context.currentTime;
      const oscillator = context.createOscillator();
      const gain = context.createGain();
      oscillator.type = "sine";
      oscillator.frequency.setValueAtTime(440, now);
      gain.gain.setValueAtTime(0.0001, now);
      gain.gain.exponentialRampToValueAtTime(0.028, now + 0.01);
      gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.13);
      oscillator.connect(gain).connect(masterRef.current!);
      oscillator.start(now);
      oscillator.stop(now + 0.15);
      oscillator.onended = () => { oscillator.disconnect(); gain.disconnect(); };
    }).catch(() => { enabledRef.current = false; setEnabled(false); });
  }, [enabled, stopAmbient]);

  useEffect(() => {
    if (enabled) startAmbient(ambientSpace);
  }, [enabled, ambientSpace, startAmbient]);

  useEffect(() => {
    const onVisibility = () => {
      const context = contextRef.current;
      if (!context) return;
      if (document.hidden) void context.suspend();
      else if (enabledRef.current) void context.resume().catch(() => { enabledRef.current = false; setEnabled(false); });
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => document.removeEventListener("visibilitychange", onVisibility);
  }, []);

  useEffect(() => () => {
    stopAmbient(0.08);
    void contextRef.current?.close();
    contextRef.current = null;
  }, [stopAmbient]);

  return { enabled, playCue, toggleSound };
}
