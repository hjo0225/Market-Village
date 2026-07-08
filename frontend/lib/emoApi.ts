// 신 감정 4축 게임(/emo/*) 클라이언트 — next.config.js rewrites로 백엔드(:8100) 프록시.
// 계약은 backend/sim/emo_api.py 시그니처와 정확히 맞춘다.
// GET은 멱등이라 1회 재시도, 상태 변이 POST는 재시도 금지(이중 적용 방지, 게이트 4c).

export interface Emotion {
  fear: number; greed: number; anxiety: number; restlessness: number;
  composure: number;   // T-37 — 평정(긍정 축)
}

export interface EmoState {
  game_id: string;
  day: number;
  total_days: number;
  clone_name: string;   // T-28 — 플레이어가 정한 클론 이름
  is_over: boolean;
  emotion: Emotion;
  verdict: string;
  portfolio_value: number;
  holdings: Record<string, number>;   // 카테고리별 보유액(T-11)
  companion: string | null;
  special_event_count: number;
  has_pending_chain: boolean;
  has_cashout_dilemma: boolean;   // T-30c
  last_market: Record<string, number>;   // T-35 — 정산일 카테고리별 수익률(%)
  ending: Ending | null;
}

export interface Dilemma { title: string; text: string; gain: boolean; choices: Choice[]; }

// position: >0 매수(담기) · <0 매도(팔기) · 0 관망 — T-35 맵 매매 fx 방향에 사용.
export interface Choice { id: string; label: string; deltas?: Record<string, number>; position?: number; }

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

// T-47d — 진단 리포트(1층 선언 vs 2층 실제 편향). 엔딩 후에만 노출.
export interface BiasComparison { axis: string; label: string; expected: number | null; actual: number; gap: number; }
export interface DiagnosisReport {
  available: boolean;
  declared_type?: string;
  capacity_score?: number;
  attitude_score?: number;
  subdimension?: { pattern: string; text: string };
  bias_comparison?: BiasComparison[];
  measured_axes?: string[];
  self_awareness?: number | null;
  insights?: string[];
  narrative?: string[];   // T-47f — LLM(또는 결정론 폴백) 리치 서술
}

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
  allocations?: Record<string, number>, name?: string,
) => postJson<EmoState>("/emo/start", { answers, seed, days, allocations, name });

export const getState = (id: string) => getJson<EmoState>(`/emo/${id}/state`);
export const getBoard = (id: string) => getJson<Board>(`/emo/${id}/board`);
export const getChain = (id: string) => getJson<ChainEvent>(`/emo/${id}/chain`);
export const chooseChain = (id: string, choice_id: string) =>
  postJson<EmoState>(`/emo/${id}/chain/choose`, { choice_id });
export const choose = (id: string, choice_id: string) =>
  postJson<EmoState>(`/emo/${id}/choose`, { choice_id });
export const getDilemma = (id: string) => getJson<Dilemma>(`/emo/${id}/dilemma`);
export const chooseDilemma = (id: string, choice_id: string) =>
  postJson<EmoState>(`/emo/${id}/dilemma/choose`, { choice_id });
export const designate = (id: string, npc_id: string) =>
  postJson<EmoState>(`/emo/${id}/designate`, { npc_id });
export const getEnding = (id: string) => getJson<Ending>(`/emo/${id}/ending`);
export const getReport = (id: string) => getJson<DiagnosisReport>(`/emo/${id}/report`);

// 감정 축 표시 메타(라벨·색·아이콘 키). 함정 4축 + 긍정 '평정'. 이모지 금지 — lucide.
export const NEGATIVE_AXES = ["fear", "greed", "anxiety", "restlessness"] as const;
export const AXES = [...NEGATIVE_AXES, "composure"] as const;
export type Axis = (typeof AXES)[number];
export const AXIS_LABEL: Record<Axis, string> = {
  fear: "공포", greed: "탐욕", anxiety: "불안", restlessness: "조급", composure: "평정",
};

// 자산 카테고리(T-11/T-30) — 시장 4카테고리 + 현금(cash). backend
// emo_game.PORTFOLIO_CATEGORIES와 일치. 스테이블(USDT)과 현금(KRW)은 분리(#3). 이모지 금지.
export const CATEGORIES = ["large_stable", "mid_alt", "meme", "stable", "cash"] as const;
export type Category = (typeof CATEGORIES)[number];
export const CATEGORY_LABEL: Record<Category, string> = {
  large_stable: "대형 안정형", mid_alt: "중견 알트형", meme: "밈형",
  stable: "스테이블(USDT)", cash: "현금(KRW)",
};

// NPC id → 표시 이름(문서 §3). 맵 8인(TRADER_PERSONAS) + 게시판 발화자
// 8인(SNS_PERSONAS) — backend personas.py와 일치. 게시판 댓글이 id(bull_hoper)로
// 뜨던 것 수정(2026-07-08): SNS 발화자도 사람 이름으로.
export const NPC_NAME: Record<string, string> = {
  panic_ant: "동수", fomo_scalper: "재훈", conspiracy_influencer: "만식",
  value_investor: "정호", quant_trader: "유리", macro_whale: "태산",
  contrarian: "미나", jackpot_gambler: "도철",
  // SNS_PERSONAS(게시판 여론 발화자)
  bull_hoper: "해나", troll: "광수", newbie: "소은", anon_veteran: "성찬",
  cheerleader: "라온", doomposter: "무경", chart_zealot: "태식", contrarian_fan: "아리",
};

// T-42 — npc_id → 초상 에셋 이름. 서버가 /assets/characters/profile/{name}.png(32×32
// 얼굴)를 서빙(프론트는 next.config rewrites로 /assets/* 프록시). AdvDialogue 좌측
// 프로필을 이 이미지로. 값은 backend/sim/personas.py의 각 persona `portrait` 필드와 일치.
export const NPC_PORTRAIT: Record<string, string> = {
  panic_ant: "Eddy_Lin", fomo_scalper: "Ryan_Park", conspiracy_influencer: "Klaus_Mueller",
  value_investor: "Adam_Smith", quant_trader: "Yuriko_Yamamoto", macro_whale: "Wolfgang_Schulz",
  contrarian: "Carmen_Ortiz", jackpot_gambler: "Carlos_Gomez",
  bull_hoper: "Hailey_Johnson", troll: "Tom_Moreno", newbie: "Maria_Lopez", anon_veteran: "Giorgio_Rossi",
  cheerleader: "Latoya_Williams", doomposter: "Arthur_Burton", chart_zealot: "Rajiv_Patel",
  contrarian_fan: "Ayesha_Khan",
};

// 초상 이미지 경로(없으면 컴포넌트가 이니셜 폴백). speakerId가 매핑에 없으면 null.
export const npcPortraitSrc = (npcId?: string): string | null =>
  npcId && NPC_PORTRAIT[npcId] ? `/assets/characters/profile/${NPC_PORTRAIT[npcId]}.png` : null;
