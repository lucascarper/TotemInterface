/** Paleta extraída da logo MultiLife: azul #164F95 e vermelho #D0080F. */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          blue: { DEFAULT: "#164F95", 50: "#EEF3FA", 100: "#D6E2F3", 200: "#A9C2E5", 600: "#164F95", 700: "#12407A", 800: "#0D2F5A", 900: "#08203D" },
          red: { DEFAULT: "#D0080F", 50: "#FDEDEE", 100: "#FAD3D5", 600: "#D0080F", 700: "#A8060C", 800: "#7E0409" },
        },
        ink: { DEFAULT: "#13213A", muted: "#5B6B85", soft: "#8A97AD" },
        surface: { DEFAULT: "#FFFFFF", alt: "#F4F7FB", line: "#DCE4EF" },
        ok: { DEFAULT: "#0F8A4B", soft: "#E3F5EB" },
        warn: { DEFAULT: "#B26A00", soft: "#FFF3DF" },
      },
      fontFamily: { sans: ["'Montserrat Variable'", "system-ui", "sans-serif"] },
      borderRadius: { xl2: "1.25rem", xl3: "1.75rem" },
      boxShadow: {
        card: "0 10px 30px -12px rgba(22,79,149,.18), 0 2px 6px -2px rgba(19,33,58,.08)",
        press: "inset 0 3px 8px rgba(0,0,0,.12)",
        soft: "0 6px 18px -8px rgba(22,79,149,.28), 0 1px 2px rgba(19,33,58,.06)",
      },
      keyframes: {
        rise: { from: { opacity: 0, transform: "translateY(14px)" }, to: { opacity: 1, transform: "none" } },
        pop: { "0%": { transform: "scale(.6)", opacity: 0 }, "70%": { transform: "scale(1.08)" }, "100%": { transform: "scale(1)", opacity: 1 } },
        pulseRing: { "0%": { transform: "scale(.9)", opacity: .7 }, "100%": { transform: "scale(1.6)", opacity: 0 } },
        shake: { "10%,90%": { transform: "translateX(-2px)" }, "20%,80%": { transform: "translateX(4px)" }, "30%,50%,70%": { transform: "translateX(-6px)" }, "40%,60%": { transform: "translateX(6px)" } },
        drain: { from: { transform: "scaleX(1)" }, to: { transform: "scaleX(0)" } },
      },
      animation: {
        rise: "rise .45s cubic-bezier(.2,.8,.2,1) both",
        pop: "pop .5s cubic-bezier(.2,.8,.2,1) both",
        pulseRing: "pulseRing 1.6s ease-out infinite",
        shake: "shake .5s both",
        drain: "drain var(--drain-duration,8s) linear forwards",
      },
    },
  },
  plugins: [],
};
