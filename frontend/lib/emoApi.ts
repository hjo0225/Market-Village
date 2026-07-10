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
  band_places?: Record<string, string>;   // T-50d — 밴드별 장소(도서관/마켓 도착 시 장소 딜레마)
  last_market: Record<string, number>;   // T-35 — 정산일 카테고리별 수익률(%)
  ending: Ending | null;
  settlement?: Settlement;   // §5.1 — 직전 정산 1회성 스냅샷(없으면 구버전 폴백, I6)
  ticker?: TickerRow[];   // v3 §B — 카테고리별 시세 현황판(없으면 티커 바 숨김, I6)
  tier?: Tier;   // v3 §C2 — 통제 티어(없으면 배지 숨김, I6)
  diagnosis?: StartDiagnosis;   // v3 §D1 — POST /start 응답에만 실림(없으면 진단 카드 스킵, I6)
}

// v3 §B — GET /emo/catalog?seed=N 응답 코인 1종. 시기(date) 정보는 절대 없음
// (엔딩 전까지 블라인드 유지). 배분 화면 실명화 + 티커 바에 사용.
export interface CatalogCoin { category: string; symbol: string; name: string; color: string; }
export interface Catalog { coins: CatalogCoin[]; }

// v3 §B — 시세 현황판 1행(카테고리당). index는 시작=100 기준 누적곱(운명선 그대로).
export interface TickerRow { category: string; symbol: string; name: string; day_pct: number; index: number; }

// v3 §C2 — 통제 티어(감정 통제 지표 기반, 상태에서 파생·저장 안 함). 5티어:
// 새싹→불개미 졸업→평정 수련→강철 멘탈→마을의 현자.
export interface Tier { name: string; icon: string; score: number; next_at: number | null; }

export interface Dilemma { title: string; text: string; gain?: boolean; choices: Choice[]; place?: string; }

// position: >0 매수(담기) · <0 매도(팔기) · 0 관망 — T-35 맵 매매 fx 방향에 사용.
export interface Choice { id: string; label: string; deltas?: Record<string, number>; position?: number; action?: "buy" | "sell" | "hold"; }

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

// §2.2 — 「오늘의 일과」 편성. forecast는 실제 정산 적용치와 동일 소스(I3) — 프론트는
// 화살표(▲/▲▲/▲▲▲, 크기 1~3)로만 시각화, badges로 확률적 요소(npc/dilemma/quiet) 표시.
export interface PlanNpcPreview { npc_id: string; name: string; portrait: string; }
export type PlanBadge = "npc" | "dilemma" | "quiet";
export interface PlanBandOption {
  place: string;
  cost: number;
  forecast: Record<string, number>;   // 축별 델타(실제 정산치와 동일 함수 출처)
  npcs: PlanNpcPreview[];
  badges: PlanBadge[];
  flavor: string;
  activity_id?: string;     // §1.2 — (밴드,장소)별 활동 변형 id. 없으면(구버전 폴백) place만 표시(I6)
  activity_name?: string;   // §1.2 — 활동명(카드 헤드라인). 없으면 place가 헤드라인(I6)
}
export interface PlanBand { band: string; options: PlanBandOption[]; }
export interface PlanFixedSlot { kind: string; label: string; }
// v2 §1 — 아침 내레이션(데이 프레임). day % 20으로 순환하는 정적 한 줄.
export interface PlanMorning { day: number; text: string; }
export interface PlanView {
  day: number;
  budget: number;
  locked: boolean;
  current_plan: Record<string, string> | null;
  fixed: Record<string, PlanFixedSlot>;
  bands: PlanBand[];
  morning: PlanMorning;
}

// §5.1 — 정산 캐스케이드 1회성 스냅샷(choose() 응답에 포함). 없으면(state.settlement
// undefined) 구버전 폴백 — DayReport는 기존 sleep→report 그대로 동작(I6).
export interface SettlementChoice { id: string; label: string; position: number; }
export interface SettlementMarketRow { category: string; pct: number; before: number; after: number; }
export interface SettlementPortfolio { before: number; after: number; pnl_pct: number; }
export interface SettlementRebalance { risk_share_before: number; risk_share_after: number; }
export interface EmotionStep { source: string; label: string; deltas: Record<string, number>; }
// v3 §C1 — 원인 카드(어제 선택 → 오늘 성과). Day 0(전날 없음)은 생략(옵셔널).
export interface Attribution {
  actual_pnl_pct: number;
  counterfactual_pnl_pct: number;
  delta_pct: number;
  cause_choice_label: string;
  text: string;
}

export interface Settlement {
  day: number;
  choice: SettlementChoice;
  market: SettlementMarketRow[];
  portfolio: SettlementPortfolio;
  rebalance: SettlementRebalance;
  emotion_steps: EmotionStep[];
  emotion_before: Record<string, number>;
  emotion_after: Record<string, number>;
  attribution?: Attribution;   // v3 §C1 — 없으면(day 0 등) 원인 카드 단계 스킵(I6)
}

// T-47d — 진단 리포트(1층 선언 vs 2층 실제 편향). 엔딩 후에만 노출.
export interface BiasComparison {
  axis: string; label: string; expected: number | null; actual: number; gap: number;
  sample?: number;   // T-48c — 측정 표본수(opportunities)
  low_sample?: boolean;   // T-48c — 임계 근접(n<5) → 신뢰 주의
}
export interface TimelineEntry { day: number; kind: string; biases: string[]; }   // T-48d
export interface BlindReveal { category: string; symbol: string; name: string; date: string; period?: string; }   // T-49c
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
  timeline?: TimelineEntry[];   // T-48d — 인과 타임라인
  blind_reveal?: BlindReveal[];   // T-49c — 엔딩 후 실제 종목·시기
  blind_reveal_headline?: string | null;   // v3 §B — 기준 장세(meme)의 시기 공개 한 줄
}

// v3 §D1 — POST /emo/start 응답에 실리는 진단 결과(설문 직후 카드). disposition.diagnose()가
// 이미 계산하는 값의 노출 + 문항별 기여 분해. 없으면(구버전 폴백) 진단 카드 스킵, 브릿지로 직행(I6).
export interface DiagnosisAxis { axis: string; label: string; score: number; max: number; }
export interface DiagnosisContribution { q: string; q_label: string; choice_label: string; axis: string; points: number; }
export interface StartDiagnosis {
  declared_type: string;
  axes: DiagnosisAxis[];
  contributions: DiagnosisContribution[];
  summary: string[];
}

export interface DispositionDiagnosis {
  answers: Record<string, number>;
  raw_score: number;
  declared_type: string;
  type_desc: string;
  risk_grade: string;
  capacity_score: number;
  attitude_score: number;
  seeds: string[];
  seed_conflicts: string[];
  expected_bias: Record<string, number>;
  source: string;
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

// T-48f — 20일 → 제품 결정으로 10일 복귀, 표본 부족은 low_sample 표시로 흡수(v3 §A).
export const startEmo = (
  answers: Record<string, number>, seed: number, days = 10,
  allocations?: Record<string, number>, name?: string,
) => postJson<EmoState>("/emo/start", { answers, seed, days, allocations, name });

export const diagnoseDisposition = (answers: Record<string, number>) =>
  postJson<DispositionDiagnosis>("/emo/diagnose", { answers });

// v3 §B — GET /emo/catalog?seed=N(신규, 멱등). 배분 화면 진입 시 seed를 먼저 뽑아
// 호출하고, 그 seed로 이후 start를 호출한다(카탈로그와 실제 게임의 시장이 일치).
export const getCatalog = (seed: number) => getJson<Catalog>(`/emo/catalog?seed=${seed}`);

export const getState = (id: string) => getJson<EmoState>(`/emo/${id}/state`);
export const getBoard = (id: string) => getJson<Board>(`/emo/${id}/board`);
export const getChain = (id: string) => getJson<ChainEvent>(`/emo/${id}/chain`);
export const chooseChain = (id: string, choice_id: string) =>
  postJson<EmoState>(`/emo/${id}/chain/choose`, { choice_id });
export const choose = (id: string, choice_id: string, coin_target?: string | null) =>
  postJson<EmoState>(`/emo/${id}/choose`, { choice_id, coin_target });
export const getDilemma = (id: string) => getJson<Dilemma>(`/emo/${id}/dilemma`);
export const chooseDilemma = (id: string, choice_id: string) =>
  postJson<EmoState>(`/emo/${id}/dilemma/choose`, { choice_id });
// T-50d — 장소 딜레마(도서관 익절복기·마켓 현실소비 = disp 결정점). 장소 도착 시.
export const getPlaceDilemma = (id: string, place: string) =>
  getJson<Dilemma>(`/emo/${id}/place_dilemma/${encodeURIComponent(place)}`);
export const choosePlaceDilemma = (id: string, place: string, choice_id: string) =>
  postJson<EmoState>(`/emo/${id}/place_dilemma/${encodeURIComponent(place)}/choose`, { choice_id });
export const designate = (id: string, npc_id: string) =>
  postJson<EmoState>(`/emo/${id}/designate`, { npc_id });
export const getEnding = (id: string) => getJson<Ending>(`/emo/${id}/ending`);
export const getReport = (id: string) => getJson<DiagnosisReport>(`/emo/${id}/report`);

// §2.2 — 「오늘의 일과」 편성. GET은 멱등(404면 아직 백엔드 미배포 → 호출부가 자동
// 편성 폴백, I6). POST는 재시도 없음(플랜은 하루 1회 잠금, I4).
export const getPlan = (id: string) => getJson<PlanView>(`/emo/${id}/plan`);
export const submitPlan = (id: string, plan: Record<string, string>) =>
  postJson<EmoState>(`/emo/${id}/plan`, { plan });

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
