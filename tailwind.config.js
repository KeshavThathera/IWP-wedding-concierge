/** Design tokens shared by every Django template. Build with `npm run build:css`. */
const plugin = require("tailwindcss/plugin");

module.exports = {
  content: ["./templates/**/*.html", "./static/js/**/*.js", "./crm/**/*.py", "./concierge/**/*.py"],
  theme: {
    extend: {
      colors: {
        ivory: "#F5EFE4",
        paper: "#FBF8F2",
        linen: "#EDE5D6",
        ink: "#1A1512",
        umber: "#2A211C",
        burgundy: "#5E1224",
        wine: "#3B0A16",
        gold: "#A8834A",
        champagne: "#D8C39A",
        charcoal: "#2B2522",
        sage: "#6F7D66",
        hairline: "#E4DACA"
      },
      fontFamily: {
        serif: ['"Cormorant Garamond"', "Georgia", "serif"],
        sans: ["Jost", "Helvetica Neue", "Arial", "sans-serif"]
      },
      letterSpacing: { luxe: ".32em", wide2: ".18em" },
      boxShadow: {
        soft: "0 30px 80px -20px rgba(26,21,18,.28)",
        card: "0 1px 2px rgba(26,21,18,.04), 0 8px 24px -12px rgba(26,21,18,.10)"
      },
      animation: {
        reveal: "reveal 1.1s cubic-bezier(.2,.7,.2,1) both",
        "slow-zoom": "slowZoom 18s ease-out both",
        "fade-in": "fadeIn .4s ease-out both",
        "rise-in": "riseIn .45s cubic-bezier(.2,.7,.2,1) both"
      },
      keyframes: {
        reveal: { from: { opacity: "0", transform: "translateY(24px)" }, to: { opacity: "1", transform: "translateY(0)" } },
        slowZoom: { from: { transform: "scale(1.08)" }, to: { transform: "scale(1)" } },
        fadeIn: { from: { opacity: "0" }, to: { opacity: "1" } },
        riseIn: { from: { opacity: "0", transform: "translateY(12px) scale(.98)" }, to: { opacity: "1", transform: "translateY(0) scale(1)" } }
      }
    }
  },
  plugins: [plugin(({ addVariant }) => addVariant("embed", ".embed &"))]
};
