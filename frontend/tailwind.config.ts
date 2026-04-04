import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#050505",
        foreground: "#f5f3ef",
        border: "rgba(255,255,255,0.1)",
        muted: "rgba(255,255,255,0.52)",
        panel: "rgba(255,255,255,0.04)",
      },
      fontFamily: {
        display: ["'Instrument Serif'", "serif"],
        body: ["'Barlow'", "sans-serif"],
      },
      boxShadow: {
        glass: "0 18px 80px rgba(0, 0, 0, 0.45)",
        glow: "0 0 0 1px rgba(255,255,255,0.08), inset 0 1px 0 rgba(255,255,255,0.12)",
      },
      backdropBlur: {
        xs: "2px",
      },
      keyframes: {
        "fade-in": {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "slide-up": {
          "0%": { opacity: "0", transform: "translateY(18px) scale(0.985)" },
          "100%": { opacity: "1", transform: "translateY(0) scale(1)" },
        },
        pulseglass: {
          "0%, 100%": { boxShadow: "0 18px 80px rgba(0, 0, 0, 0.45)" },
          "50%": { boxShadow: "0 24px 96px rgba(255, 255, 255, 0.05)" },
        },
      },
      animation: {
        "fade-in": "fade-in 0.55s ease forwards",
        "slide-up": "slide-up 0.55s cubic-bezier(0.22, 1, 0.36, 1) forwards",
        pulseglass: "pulseglass 5s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
