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

export interface Portfolio {
  avg_cost: number; quantity: number; cash: number;
  positions?: Record<string, { avg_cost: number; quantity: number }>;
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
export interface DayResult {
  trap: string | null; swayed: boolean; fund_flow: string;
  realized_pnl: number; stats: CloneStats;
}
export interface Scene { commands: unknown[]; dialogue: string; monologue_open: boolean; }

export const api = {
  // -- 인터뷰 --
  interviewNext: (sessionId: string, useLlm = false) =>
    get<{ status: string; done: boolean; next?: { id: string; text: string }; answers?: Record<string, number> }>(
      "/control/interview/next", { session_id: sessionId, use_llm: useLlm }),
  interviewAnswer: (sessionId: string, qid: string, text: string, useLlm = false) =>
    post<{ status: string; done: boolean; next?: { id: string; text: string }; answers?: Record<string, number> }>(
      "/control/interview/answer", { session_id: sessionId, qid, text, use_llm: useLlm }),

  // -- 게임 세션 --
  gameStart: (gameId: string, answers: Record<string, number>, symbol: string, startPrice = 100.0) =>
    post<{ status: string; state: GameState }>(
      "/control/game/start", { game_id: gameId, answers, symbol, start_price: startPrice }),
  gameState: (gameId: string) =>
    get<{ status: string; state: GameState }>("/control/game/state", { game_id: gameId }),
  gamePreview: (gameId: string) =>
    get<{ status: string; slots: unknown[]; schedule: Record<string, string>; meetings: Meetings; picks: Picks }>(
      "/control/game/day/preview", { game_id: gameId }),
  gameAvoid: (gameId: string, slotA: number, slotB: number) =>
    post<{ status: string; schedule: Record<string, string>; meetings: Meetings }>(
      "/control/game/day/avoid", { game_id: gameId, slot_a: slotA, slot_b: slotB }),
  gameNews: (gameId: string, seed = 0) =>
    get<{ status: string; news: NewsItem[] }>("/control/game/news", { game_id: gameId, seed }),
  gameCrisisCheck: (gameId: string, newsId?: string) =>
    get<{ status: string; trap: string | null; trap_name: string | null }>(
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
  gameCompare: (gameId: string, runA: string, runB: string, day: number) =>
    get<{ status: string; a: unknown; b: unknown }>(
      "/control/game/compare", { game_id: gameId, run_a: runA, run_b: runB, day }),
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
