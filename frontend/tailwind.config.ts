import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          DEFAULT: "#0a0b0d",
          900: "#0a0b0d",
          800: "#101114",
          700: "#16181c",
          600: "#1d2025",
          500: "#262a30",
        },
        signal: { DEFAULT: "#cdf24e", dim: "#a6c43c", glow: "#e6ff7a" },
        paper: "#ecebe6",
        dim: "#9b9d98",
        faint: "#62656c",
        ok: "#86e08a",
        run: "#6cb6ff",
        warn: "#e8b339",
        err: "#ff7d72",
        idle: "#6b7077",
      },
      fontFamily: {
        sans: ["var(--font-plex-sans)", "ui-sans-serif", "system-ui"],
        mono: ["var(--font-plex-mono)", "ui-monospace", "monospace"],
        display: ["var(--font-bricolage)", "ui-sans-serif", "system-ui"],
      },
      letterSpacing: { tightest: "-0.04em" },
      borderRadius: { md: "6px", lg: "10px" },
      boxShadow: {
        panel: "0 1px 0 0 rgba(255,255,255,0.04) inset, 0 24px 60px -30px rgba(0,0,0,0.85)",
        glow: "0 0 0 1px rgba(205,242,78,0.35), 0 0 22px -4px rgba(205,242,78,0.35)",
      },
      keyframes: {
        rise: {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: { "100%": { transform: "translateX(100%)" } },
        pulseDot: { "0%,100%": { opacity: "1" }, "50%": { opacity: "0.25" } },
        sweep: { "0%": { transform: "scaleX(0)" }, "100%": { transform: "scaleX(1)" } },
      },
      animation: {
        rise: "rise 0.55s cubic-bezier(0.2,0.7,0.2,1) both",
        shimmer: "shimmer 1.4s infinite",
        pulseDot: "pulseDot 1.8s ease-in-out infinite",
        sweep: "sweep 0.7s cubic-bezier(0.2,0.7,0.2,1) both",
      },
    },
  },
  plugins: [],
};

export default config;
