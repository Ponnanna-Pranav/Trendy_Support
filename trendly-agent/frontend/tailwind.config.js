/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          DEFAULT: "#15151A",
          soft: "#3A3A42",
        },
        paper: {
          DEFAULT: "#F3F2EE",
          raised: "#FBFAF8",
        },
        berry: {
          DEFAULT: "#C81E5C",
          soft: "#F4D9E4",
          dark: "#9C1748",
        },
        moss: {
          DEFAULT: "#1F7A5B",
          soft: "#DCEEE6",
        },
        amber: {
          DEFAULT: "#B8791A",
          soft: "#F4E6CF",
        },
        rule: "#DCDAD3",
      },
      fontFamily: {
        display: ["Fraunces", "serif"],
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["'IBM Plex Mono'", "monospace"],
      },
      borderRadius: {
        card: "14px",
      },
      boxShadow: {
        panel: "0 20px 60px -20px rgba(21,21,26,0.35)",
        launcher: "0 10px 30px -8px rgba(21,21,26,0.45)",
      },
      keyframes: {
        rise: {
          "0%": { opacity: 0, transform: "translateY(8px)" },
          "100%": { opacity: 1, transform: "translateY(0)" },
        },
        panelIn: {
          "0%": { opacity: 0, transform: "translateY(16px) scale(0.98)" },
          "100%": { opacity: 1, transform: "translateY(0) scale(1)" },
        },
        pulseDot: {
          "0%, 80%, 100%": { transform: "scale(0.6)", opacity: 0.4 },
          "40%": { transform: "scale(1)", opacity: 1 },
        },
      },
      animation: {
        rise: "rise 0.25s ease-out",
        panelIn: "panelIn 0.22s cubic-bezier(.2,.8,.2,1)",
        pulseDot: "pulseDot 1.2s infinite ease-in-out",
      },
    },
  },
  plugins: [],
};
