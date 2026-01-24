export const copy = {
  system: {
    status: {
      operational: "OPERATIONAL",
      degraded: "DEGRADED",
      error: "SYSTEM FAILURE",
      booting: "BOOTING",
      synthesizing: "Synthesizing compounds…"
    },
    errors: {
      todayLoad: "TODAY JSON load failed",
      archiveLoad: "ARCHIVE JSON load failed",
      bsodTitle: "Critical Data Fault",
      bsodBody: "System failure. Patient advised to remain calm while diagnostics rerun.",
      errorCode: "ERROR_CODE: 0xTRI-ARCHIVE"
    },
    marqueeFallback: ["Triangulum intake stable", "Awaiting signals", "Scan ready"]
  },
  hud: {
    labels: {
      batchId: "Batch ID",
      status: "Status"
    },
    clock: {
      nextCycle: "NEXT CYCLE",
      tMinus: "T-MINUS"
    }
  },
  today: {
    label: "Today",
    headerFallback: "Calibrating today’s triage",
    intro:
      "Diagnostic pipeline engaged. Three capsules are compiled in sequence for immediate intake.",
    loading: "Synthesizing compounds…",
    themePrefix: "Theme",
    timeline: {
      title: "Today Timeline",
      thumb: "Slot",
      nowLabel: "Now"
    },
    returnToNow: "Return to now",
    ambientEnter: "Enter ambient",
    ambientExit: "Exit ambient"
  },
  archive: {
    label: "Patient Records",
    selectDate: "Select a date",
    intro: "Historical intake logs. Select a date to replay the triage output.",
    datesLabel: "Dates",
    loadingIndex: "Synthesizing archive index…",
    empty: "Select a date to view archived capsules."
  },
  treatment: {
    dose: {
      readminister: "Re-administer Dose"
    },
    viewer: {
      enter: "Administering dose…",
      close: "Close viewer",
      exit: "Disengage viewer",
      prev: "Previous dose",
      next: "Next dose",
      instructions: "Use arrows or click zones to cycle."
    },
    slot: {
      Headliner: "Headliner",
      Lineage: "Lineage",
      DeepCut: "Deep Cut"
    },
    cover: {
      missing: "No Cover",
      unknownArtist: "Unknown Artist"
    },
    links: {
      musicbrainz: "MusicBrainz",
      youtube: "YouTube"
    }
  }
} as const;

export type CopySchema = typeof copy;
