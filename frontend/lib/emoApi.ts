// 신 감정 4축 게임(/emo/*) 클라이언트 — next.config.js rewrites로 백엔드(:8100) 프록시.
// 계약은 backend/sim/emo_api.py 시그니처와 정확히 맞춘다.
// GET은 멱등이라 1회 재시도, 상태 변이 POST는 재시도 금지(이중 적용 방지, 게이트 4c).

export interface Emotion {
  fear: number; greed: number; anxiety: number; restlessness: number;
}

export interface EmoState {
  game_id: string;
  day: number;
  total_days: number;
  is_over: boolean;
  emotion: Emotion;
  verdict: string;
  portfolio_value: number;
  holdings: Record<string, number>;   // 카테고리별 보유액(T-11)
  companion: string | null;
  special_event_count: number;
  has_pending_chain: boolean;
  ending: Ending | null;
}

export interface Choice { id: string; label: string; deltas?: Record<string, number>; }

export interface Board {
  event_id: string;
  context: string;
  verdict: string;
  threads: { author_id: string; stance: string; text: string; comments: { author_id: string; stance: string; text: string }[] }[];
  scenario: { text: string; choices: Choice[] };
}

export interface ChainEvent {
  npc_id: string; stage: number; place?: string; title: string; text: string;
  choices: Choice[]; info?: string | null;
}

export interface Ending { id: string; title: string; grade: string; epilogue: string[]; }

async function fetchJson<T>(input: RequestInfo, init?: RequestInit, retries = 1): Promise<T | null> {
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const r = await fetch(input, init);
      if (r.ok) return (await r.json()) as T;
      if (r.status === 404 || r.status === 409 || r.status === 400) return null;
    } catch {
      /* 네트워크 오류 */
    }
    if (attempt < retries) await new Promise((res) => setTimeout(res, 400));
  }
  return null;
}

const getJson = <T>(path: string) => fetchJson<T>(path, { cache: "no-store" }, 1);
const postJson = <T>(path: string, body: Record<string, unknown>) =>
  fetchJson<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }, 0); // 변이는 재시도 없음

export const startEmo = (
  answers: Record<string, number>, seed: number, days = 10,
  allocations?: Record<string, number>,
) => postJson<EmoState>("/emo/start", { answers, seed, days, allocations });

export const getState = (id: string) => getJson<EmoState>(`/emo/${id}/state`);
export const getBoard = (id: string) => getJson<Board>(`/emo/${id}/board`);
export const getChain = (id: string) => getJson<ChainEvent>(`/emo/${id}/chain`);
export const chooseChain = (id: string, choice_id: string) =>
  postJson<EmoState>(`/emo/${id}/chain/choose`, { choice_id });
export const choose = (id: string, choice_id: string) =>
  postJson<EmoState>(`/emo/${id}/choose`, { choice_id });
export const designate = (id: string, npc_id: string) =>
  postJson<EmoState>(`/emo/${id}/designate`, { npc_id });
export const getEnding = (id: string) => getJson<Ending>(`/emo/${id}/ending`);

// 감정 4축 표시 메타(라벨·색·아이콘 키). 이모지 금지 — lucide 아이콘.
export const AXES = ["fear", "greed", "anxiety", "restlessness"] as const;
export type Axis = (typeof AXES)[number];
export const AXIS_LABEL: Record<Axis, string> = {
  fear: "공포", greed: "탐욕", anxiety: "불안", restlessness: "조급",
};

// 자산 카테고리(T-11) — backend fate_line.CATEGORIES와 정확히 일치. 이모지 금지.
export const CATEGORIES = ["large_stable", "mid_alt", "meme", "stable"] as const;
export type Category = (typeof CATEGORIES)[number];
export const CATEGORY_LABEL: Record<Category, string> = {
  large_stable: "대형 안정형", mid_alt: "중견 알트형", meme: "밈형", stable: "스테이블/현금",
};

// NPC id → 표시 이름(문서 §3).
export const NPC_NAME: Record<string, string> = {
  panic_ant: "동수", fomo_scalper: "재훈", conspiracy_influencer: "만식",
  value_investor: "정호", quant_trader: "유리", macro_whale: "태산",
  contrarian: "미나", jackpot_gambler: "도철",
};
