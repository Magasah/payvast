import type { Config } from "tailwindcss";

const token = (name: string) => `rgb(var(--c-${name}) / <alpha-value>)`;

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    // Type scale: 1.25 ratio on a 16px base (13 / 16 / 20 / 25 / 31 / 39 / 49 / 61).
    fontSize: {
      xs: ["0.8125rem", { lineHeight: "1.25rem" }],
      sm: ["0.9375rem", { lineHeight: "1.4rem" }],
      base: ["1rem", { lineHeight: "1.6rem" }],
      lg: ["1.25rem", { lineHeight: "1.75rem" }],
      xl: ["1.5625rem", { lineHeight: "2rem" }],
      "2xl": ["1.9375rem", { lineHeight: "2.3rem" }],
      "3xl": ["2.4375rem", { lineHeight: "2.75rem" }],
      "4xl": ["3.0625rem", { lineHeight: "3.25rem" }],
      "5xl": ["3.8125rem", { lineHeight: "3.9rem" }],
    },
    colors: {
      transparent: "transparent",
      current: "currentColor",
      white: "#ffffff",
      paper: token("paper"),
      surface: token("surface"),
      ink: { DEFAULT: token("ink"), soft: token("ink-soft") },
      line: token("line"),
      lapis: { DEFAULT: token("lapis"), deep: token("lapis-deep"), tint: token("lapis-tint") },
      pomegranate: { DEFAULT: token("pomegranate"), tint: token("pomegranate-tint") },
      saffron: { DEFAULT: token("saffron"), tint: token("saffron-tint") },
      pistachio: { DEFAULT: token("pistachio"), tint: token("pistachio-tint") },
    },
    borderRadius: {
      none: "0",
      sm: "6px", // badges
      md: "12px", // controls: buttons, inputs
      lg: "20px", // panels
      pass: "28px", // the subscription pass only
      full: "9999px",
    },
    extend: {
      fontFamily: {
        display: ['"Commissioner Flair"', "Georgia", "serif"],
        text: ['"Golos Text"', "system-ui", "-apple-system", "Segoe UI", "Roboto", "sans-serif"],
      },
      maxWidth: { page: "68rem", prose: "38rem" },
      letterSpacing: { display: "-0.02em" },
    },
  },
  plugins: [],
};

export default config;
