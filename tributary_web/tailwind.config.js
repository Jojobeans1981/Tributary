/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        abyss: "#0A2E36",
        deep: "#0D4F5C",
        current: "#0E7C8B",
        surface: "#12A8BC",
        foam: "#C8EEF2",
        mist: "#EDF8FA",
        amber: "#F07800",
        dawn: "#FFF3E0",
        obsidian: "#0F1923",
        slate: "#2C3E50",
        stone: "#5D7078",
        pebble: "#A0B4BB",
        sand: "#E8EEF0",
        chalk: "#F7FAFB",
        go: "#1A6B3C",
        "go-light": "#D4EDDA",
        stop: "#A31515",
        "stop-light": "#FDECEA",
        caution: "#C45E00",
        "caution-light": "#FFF3CD",
      },
      fontFamily: {
        display: ["Georgia", "serif"],
        body: ["Arial", "sans-serif"],
      },
      boxShadow: {
        card: "0 2px 8px rgba(10,46,54,0.08)",
        "card-hover": "0 4px 16px rgba(10,46,54,0.14)",
      },
      borderRadius: {
        card: "8px",
        input: "6px",
        badge: "6px",
      },
    },
  },
  plugins: [],
};
