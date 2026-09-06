import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        "void-black": "#050505",
        "clinical-white": "#F0F0F0",
        "signal-accent": "#A8C700",
        "alert-red": "#FF3300",
        "panel-900": "#0C0C0C",
        "panel-800": "#121212",
        "panel-700": "#1A1A1A"
      },
      fontFamily: {
        display: ["Space Grotesk", "Triangulum Noto Sans SC", "Noto Sans SC", "PingFang SC", "Microsoft YaHei", "sans-serif"],
        mono: ["IBM Plex Mono", "Triangulum Sarasa Mono SC", "Sarasa Mono SC", "Microsoft YaHei UI", "ui-monospace", "SFMono-Regular", "Menlo", "monospace"]
      },
      letterSpacing: {
        tightish: "-0.02em",
        tracker: "0.24em"
      },
      borderRadius: {
        hud: "6px",
        card: "18px"
      },
      boxShadow: {
        "hard-xl": "0 24px 60px rgba(0,0,0,0.65)",
        "hard-lg": "0 12px 32px rgba(0,0,0,0.5)"
      },
      outline: {
        "signal": "2px solid #A8C700"
      }
    }
  },
  plugins: []
} satisfies Config;
