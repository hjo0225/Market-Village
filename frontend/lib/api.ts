// 백엔드(FastAPI :8100) 클라이언트 — next.config.js의 rewrites로 /control/* 프록시.
// 계약은 backend/market_live_server.py의 실제 엔드포인트 시그니처와 정확히 맞춘다.
//
// Next.js dev의 rewrites 프록시가 Windows에서 백엔드로의 아웃바운드 연결에
// 간헐적으로 EFAULT를 내는 걸 이 세션에서 반복 관찰(map.html에도 같은 방어가
// 있음, RETRO 참고) — 여기서도 1회 자동 재시도한다.
async function fetchJson<T>(input: RequestInfo, init?: RequestInit): Promise<T> {
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const r = await fetch(input, init);
      if (r.ok) return (await r.json()) as T;
    } catch {
      /* 네트워크 오류 — 재시도 */
    }
    if (attempt === 0) await new Promise((res) => setTimeout(res, 400));
  }
  return { status: "error", error: "network" } as T;
}

async function get<T>(path: string, params: Record<string, string | number | boolean | undefined> = {}): Promise<T> {
  const qs = Object.entries(params)
    .filter(([, v]) => v !== undefined)
    .map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`)
    .join("&");
  return fetchJson<T>(path + (qs ? `?${qs}` : ""), { cache: "no-store" });
}

async function post<T>(path: string, body: Record<string, unknown>): Promise<T> {
  return fetchJson<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export interface CloneStats {
  [key: string]: number;
  급락패닉저항: number; 멘탈마모저항: number; 익절거부제어: number;
  과대베팅제어: number; 추격매수저항: number; 막차불안저항: number; 멘탈회복: number;
}

// PRD §6.2 — 4카테고리 한글 라벨(백엔드 category 슬러그 → 표시용).
export const CATEGORY_LABELS: Record<string, string> = {
  large_stable: "대형 안정형", mid_alt: "중견 알트형", meme: "밈형", stable: "스테이블",
};

// §8.3 자금 행선지 라벨 — DayResultToast·회차 비교(T-227)가 공유하는 단일 소스.
export const FUND_FLOW_LABELS: Record<string, string> = {
  to_cash: "공포 매도 → 현금 도피",
  to_stable: "공포 매도 → 스테이블 이동",
  to_hotter: "충동 추격 → 급등 종목에 새로 태움",
  concentrate: "몰빵 → 기존 포지션 더 매수",
  hold_winner: "익절 거부 → 계속 보유",
};

// §9.5.3 NPC id → 표시명 (backend/sim/personas.py와 동일해야 한다).
export const NPC_LABELS: Record<string, string> = {
  panic_ant: "패닉셀 개미", fomo_scalper: "FOMO 단타러",
  conspiracy_influencer: "음모론 인플루언서", value_investor: "가치투자자",
  quant_trader: "퀀트 트레이더", macro_whale: "매크로 고래",
  contrarian: "역발상 투자자", jackpot_gambler: "한탕 도박꾼",
};

export interface PortfolioHolding {
  category: string; quantity: number; avg_cost: number; value: number; unrealized_pnl: number;
}

export interface Portfolio {
  avg_cost: number; quantity: number; cash: number;
  positions?: Record<string, { avg_cost: number; quantity: number }>;
  holdings: PortfolioHolding[];
}

export interface GameState {
  run_id: string; day: number; days: number; finished: boolean;
  stats: CloneStats; portfolio: Portfolio; total_asset: number;
  category: string; last_event: { delta: number; text?: string } | null;
  rapport: number; crowd_mood: number;
}

export interface NewsItem { id: string; tone: string; headline: string; }
export interface Meetings { [slot: string]: string[]; }
export interface Picks { [slot: string]: string | null; }
export interface ResultCard {
  return_pct: number; grade: string; emotion_overall: CloneStats; evaluation: string;
}
export interface RunSummary {
  run_id: string; return_pct: number; grade: string;
  emotion_overall: Record<string, number>; trap_counts: Record<string, unknown>;
  clone_spec_snapshot: Record<string, number>;
}
export interface BundleItem {
  category: string; trap: string | null; trap_name: string | null;
  resisted: boolean; reason: string; fund_flow: string; realized_pnl: number;
}
export interface DayResult {
  trap: string | null; swayed: boolean; fund_flow: string;
  realized_pnl: number; stats: CloneStats; bundle: BundleItem[];
}
export interface Scene { commands: unknown[]; dialogue: string; monologue_open: boolean; }
// T-227 §13.6 — GET /control/game/compare의 회차별 하루 뷰.
export interface CompareDayView {
  swayed: boolean; companion: string; fund_flow: string;
  realized_pnl: number; total_asset: number;
}
// T-224 게시판(SNS형 FGI) — GET /control/game/day/board 계약(PRD_SOCIAL_NPC_BOARD §3.2).
export interface BoardComment { author: string; author_id: string; text: string; }
export interface BoardPost {
  author: string; author_id: string; author_kind: "sns" | "clone";
  portrait: string | null; text: string; comments: BoardComment[];
}
export interface BoardFeed {
  day: number; open: boolean; context: string | null;
  posts: BoardPost[]; crowd_mood_delta: number;
}

export const api = {
  // -- 인터뷰 --
  interviewNext: (sessionId: string, useLlm = false) =>
    get<{ status: string; done: boolean; next?: { id: string; text: string }; answers?: Record<string, number> }>(
      "/control/interview/next", { session_id: sessionId, use_llm: useLlm }),
  interviewAnswer: (sessionId: string, qid: string, text: string, useLlm = false) =>
    post<{ status: string; done: boolean; next?: { id: string; text: string }; answers?: Record<string, number> }>(
      "/control/interview/answer", { session_id: sessionId, qid, text, use_llm: useLlm }),

  // -- 게임 세션 --
  gameStart: (
    gameId: string, answers: Record<string, number>, symbol: string, startPrice = 100.0,
    allocations?: Record<string, number>,
  ) =>
    post<{ status: string; state: GameState }>(
      "/control/game/start",
      { game_id: gameId, answers, symbol, start_price: startPrice, allocations: allocations ?? null }),
  gameState: (gameId: string) =>
    get<{ status: string; state: GameState }>("/control/game/state", { game_id: gameId }),
  gamePreview: (gameId: string) =>
    get<{ status: string; slots: unknown[]; schedule: Record<string, string>; meetings: Meetings; picks: Picks }>(
      "/control/game/day/preview", { game_id: gameId }),
  gameAvoid: (gameId: string, slotA: number, slotB: number) =>
    post<{ status: string; schedule: Record<string, string>; meetings: Meetings }>(
      "/control/game/day/avoid", { game_id: gameId, slot_a: slotA, slot_b: slotB }),
  // seed 생략 시 서버가 (game_id, day)로 파생 — 같은 날 안정, 날마다 새 3개(T-223).
  gameNews: (gameId: string, seed?: number) =>
    get<{ status: string; news: NewsItem[] }>("/control/game/news", { game_id: gameId, seed }),
  // T-227 §13.6 회차 비교 — 분기일 목록 + 특정 날의 두 회차 겹쳐보기.
  gameCompareDays: (gameId: string, runA: string, runB: string) =>
    get<{ status: string; days: number[] }>(
      "/control/game/compare_days", { game_id: gameId, run_a: runA, run_b: runB }),
  gameCompare: (gameId: string, runA: string, runB: string, day: number) =>
    get<{ status: string; day: number; a: CompareDayView | null; b: CompareDayView | null }>(
      "/control/game/compare", { game_id: gameId, run_a: runA, run_b: runB, day }),
  gameBoard: (gameId: string, useLlm = false) =>
    get<{ status: string } & BoardFeed>("/control/game/day/board", { game_id: gameId, use_llm: useLlm }),
  gameCrisisCheck: (gameId: string, newsId?: string) =>
    get<{ status: string; trap: string | null; trap_name: string | null;
         bundle: { category: string; trap: string; trap_name: string }[] }>(
      "/control/game/day/crisis_check", { game_id: gameId, news_id: newsId }),
  gameAdvance: (gameId: string, opts: { newsId?: string; strategy?: string; rapport?: number; roll?: number } = {}) =>
    post<{ status: string; state: GameState; day_result?: DayResult; card?: ResultCard }>(
      "/control/game/day/advance", {
        game_id: gameId, news_id: opts.newsId ?? null, strategy: opts.strategy ?? null,
        // rapport를 null로 보내면 백엔드가 GameRun의 실제 공유 래포 풀을 쓴다
        // (opts.rapport를 넘기지 않는 게 일반 플레이의 기본 경로).
        rapport: opts.rapport ?? null, roll: opts.roll ?? Math.random() * 100,
      }),
  gameScene: (gameId: string, useLlm = false) =>
    get<{ status: string; scene?: Scene }>("/control/game/day/scene", { game_id: gameId, use_llm: useLlm }),
  gameCard: (gameId: string) =>
    get<{ status: string; card?: ResultCard }>("/control/game/card", { game_id: gameId }),
  gameNewRun: (gameId: string, runId?: string) =>
    post<{ status: string; state: GameState }>("/control/game/newrun", { game_id: gameId, run_id: runId ?? null }),
  gameSummaries: (gameId: string) =>
    get<{ status: string; summaries: RunSummary[] }>("/control/game/summaries", { game_id: gameId }),

  // -- 핸드폰(§9.1b) --
  persuade: (gameId: string, npcId: string, direction: "calm" | "escalate", roll = 50.0) =>
    post<{ status: string; accepted: boolean; success_prob: number; rapport: number }>(
      "/control/game/social/persuade", { game_id: gameId, npc_id: npcId, direction, roll }),
  fgi: (gameId: string, tone: string, roll = 20.0) =>
    post<{ status: string; crowd_mood: number; clone_delta_applied: number; absorbed: boolean }>(
      "/control/game/social/fgi", { game_id: gameId, tone, roll }),
};

export const STAT_LABELS: (keyof CloneStats)[] = [
  "급락패닉저항", "멘탈마모저항", "익절거부제어", "과대베팅제어", "추격매수저항", "막차불안저항", "멘탈회복",
];
