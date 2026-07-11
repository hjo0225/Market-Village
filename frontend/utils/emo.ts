import { Category, CATEGORIES } from "@/lib/emoApi";
import { LevelMap } from "@/types/emo";
import { LEVEL_WEIGHT, TRADE_FX_MIN } from "@/constants/emo";

// 게시판 반응 position → 매매 태그(임계 미만은 관망).
export const positionTag = (pos: number): "buy" | "sell" | "hold" =>
  pos >= TRADE_FX_MIN ? "buy" : pos <= -TRADE_FX_MIN ? "sell" : "hold";

// 배분 레벨 → 카테고리별 상대 가중치(백엔드가 합으로 정규화).
export const levelWeights = (levels: LevelMap): Record<string, number> => {
  const w: Record<string, number> = {};
  CATEGORIES.forEach((c: Category) => { w[c] = LEVEL_WEIGHT[levels[c]]; });
  return w;
};

// T-66 — 게임 일수 → 자연스러운 한국어 표현("사흘"/"열흘"/그 외 "N일").
export const daysWord = (n: number): string =>
  n === 3 ? "사흘" : n === 10 ? "열흘" : `${n}일`;
