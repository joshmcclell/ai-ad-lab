import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // FlowBase brand palette (docs/01-business-and-branding.md)
        brand: { DEFAULT: "#2563EB", accent: "#0EA5E9" },
        ink: "#0F172A",
        surface: "#F8FAFC",
      },
    },
  },
  plugins: [],
};

export default config;
