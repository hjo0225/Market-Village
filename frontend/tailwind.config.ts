import type { Config } from "tailwindcss";

/**
 * DESIGN.md — 흰 베이스, 흑백 카드, 그린/옐로는 액센트 전용.
 * (market_aquarium 프로젝트의 디자인 토큰을 그대로 이식 — 프레임워크 무관 토큰이라 재사용)
 */
const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        black: "#161616",
        white: "#FFFFFF",
        green: {
          50: "#E8F8DC", 100: "#B7EE8C", 200: "#78F142", 400: "#4FA82A",
          600: "#327A1C", 800: "#1E4D11", 900: "#143408",
        },
        yellow: {
          50: "#FFF6D6", 100: "#FFE87C", 200: "#FFD23F", 400: "#E0A41E",
          600: "#A8741A", 800: "#6E4B12", 900: "#4A310B",
        },
        slate: {
          50: "#F8FAFC", 100: "#F2F4F7", 200: "#E4E7EC", 300: "#CBD5E1",
          400: "#AEB4BD", 500: "#6B7280", 600: "#4B5563", 700: "#374151",
          800: "#2F343B", 900: "#161616",
        },
        pixel: {
          grass: "#78F142",
          path: "#F2F4F7",
          paper: "#FFFFFF",
          wall: "#FFFFFF",
          table: "#FFFFFF",
          border: "#161616",
          water: "#E8F8DC",
          danger: "#6E4B12",
          ink: "#161616",
          inkSoft: "#2A2D31",
          cloud: "#FFFFFF",
          muted: "#6B7280",
          mutedDark: "#AEB4BD",
          greenText: "#327A1C",
          gold: "#A8741A",
        },
      },
      fontFamily: {
        sans: ["Pretendard Variable", "Pretendard", "system-ui", "sans-serif"],
      },
      borderRadius: {
        none: "0", sm: "8px", DEFAULT: "12px", md: "12px", lg: "16px",
        xl: "20px", "2xl": "24px", "3xl": "28px", full: "9999px",
      },
      boxShadow: {
        "pixel-sm": "2px 2px 0 0 #161616",
        "pixel-md": "3px 3px 0 0 #161616",
        "pixel-lg": "5px 5px 0 0 #161616",
        phone: "6px 6px 0 0 #161616",
      },
    },
  },
  plugins: [],
};
export default config;
