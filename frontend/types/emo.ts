import { Category } from "@/lib/emoApi";

// 초기 배분 UX — 슬라이더 대신 높음/중간/낮음(가중치).
export type Level = "low" | "med" | "high";
export type LevelMap = Record<Category, Level>;

// 성향 진단 문항 + 코인 초보용 친절 설명 힌트.
export type Question = { key: string; text: string; options: [string, number][] };
export type QuestionHint = { title: string; text: string };
