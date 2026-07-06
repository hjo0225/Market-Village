// 백엔드(FastAPI :8100) 클라이언트 — next.config.js의 rewrites로 /control/* 프록시.
// 계약은 backend/market_live_server.py의 실제 엔드포인트 시그니처와 정확히 맞춘다.
//
// Next.js dev의 rewrites 프록시가 Windows에서 백엔드로의 아웃바운드 연결에
// 간헐적으로 EFAULT를 내는 걸 이 세션에서 반복 관찰(map.html에도 같은 방어가
// 있음, RETRO 참고) — 조회(GET)는 1회 자동 재시도한다.
// T-258 — 상태 변이 POST는 재시도 금지(멱등성): 요청이 서버에 적용된 뒤 응답만
// 유실되면 재시도가 이중 적용된다(/day/advance면 하루가 2번 감). CLAUDE.md 게이트 4c.
async function fetchJson<T>(input: RequestInfo, init?: RequestInit, retries = 1): Promise<T> {
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const r = await fetch(input, init);
      if (r.ok) return (await r.json()) as T;
    } catch {
      /* 네트워크 오류 — retries 남았으면 재시도 */
    }
    if (attempt < retries) await new Promise((res) => setTimeout(res, 400));
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
  }, 0);   // T-258 — 변이 요청은 재시도 없음
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

// §8.3 자금 행선지 라벨 — DayResultModal·회차 비교(T-227)가 공유하는 단일 소스.
export const FUND_FLOW_LABELS: Record<string, string> = {
  to_cash: "공포 매도 → 현금 도피",
  to_stable: "공포 매도 → 스테이블 이동",
  to_hotter: "충동 추격 → 급등 종목에 새로 태움",
  concentrate: "몰빵 → 기존 포지션 더 매수",
  hold_winner: "익절 거부 → 계속 보유",
};

// §9.5.3 NPC id → 표시명(T-246 사람 이름 — backend/sim/personas.py와 동일해야 한다).
export const NPC_LABELS: Record<string, string> = {
  panic_ant: "동수", fomo_scalper: "재훈",
  conspiracy_influencer: "만식", value_investor: "정호",
  quant_trader: "유리", macro_whale: "태산",
  contrarian: "미나", jackpot_gambler: "도철",
};
// NPC id → 역할명(부기 표기용 — 이름만으론 성격을 모르니 괄호로 병기).
export const NPC_ROLES: Record<string, string> = {
  panic_ant: "패닉셀 개미", fomo_scalper: "FOMO 단타러",
  conspiracy_influencer: "음모론 인플루언서", value_investor: "가치투자자",
  quant_trader: "퀀트 트레이더", macro_whale: "매크로 고래",
  contrarian: "역발상 투자자", jackpot_gambler: "한탕 도박꾼",
};

// T-288 — 메신저 아바타(초상 파일명, backend personas.portrait와 동일).
export const NPC_PORTRAITS: Record<string, string> = {
  panic_ant: "Eddy_Lin", fomo_scalper: "Ryan_Park",
  conspiracy_influencer: "Klaus_Mueller", value_investor: "Adam_Smith",
  quant_trader: "Yuriko_Yamamoto", macro_whale: "Wolfgang_Schulz",
  contrarian: "Carmen_Ortiz", jackpot_gambler: "Carlos_Gomez",
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
// T-272a — 플레이어가 지정한 대화 상대(슬롯→npc id). 없으면 클론이 고른다.
export interface Designated { [slot: string]: string; }

// T-269 — 발자취(진행 이력 패널).
export interface SocialAction {
  day: number; kind: "persuade" | "fgi";
  npc_id?: string; direction?: string; accepted?: boolean; tone?: string;
}
export interface HistoryDay {
  day: number; news_id: string; news_tone: string;
  met: string[]; companion: string;
  schedule: Record<string, string>;
  swayed: boolean; trap: string | null;
  social: SocialAction[];
}
export interface ChatLogEntry {
  kind: "meeting" | "persuade";
  lines?: { who: "npc" | "clone"; text: string }[];
  direction?: string; accepted?: boolean;
}
export interface ChatLogDay { day: number; entries: ChatLogEntry[] }

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
export interface BoardComment {
  author: string; author_role?: string | null; author_id: string;
  stance?: string | null;   // T-251 — up/down/split(가격 전망)
  text: string;
}
export interface BoardPost {
  author: string; author_role?: string | null; author_id: string; author_kind: "sns" | "clone";
  portrait: string | null; stance?: string | null; text: string; comments: BoardComment[];
}
export interface BoardFeed {
  day: number; open: boolean; context: string | null;
  verdict?: "up" | "down" | "split";   // T-251 — 대화의 다수 결론
  posts: BoardPost[]; crowd_mood_delta: number;
  // T-257 — 닫힌 날 핸드폰 게시판 탭용: 가장 최근 박제 대화(읽기 전용, 클론 미주입).
  recent?: { day: number; posts: BoardPost[] } | null;
}

export const api = {
  // -- 인터뷰 --
  interviewNext: (sessionId: string, useLlm = false) =>
    get<{ status: string; done: boolean; next?: { id: string; text: string }; answers?: Record<string, number> }>(
      "/control/interview/next", { session_id: sessionId, use_llm: useLlm }),
  interviewAnswer: (sessionId: string, qid: string, text: string, useLlm = false) =>
    post<{ status: string; done: boolean; next?: { id: string; text: string }; answers?: Record<string, number> }>(
      "/control/interview/answer", { session_id: sessionId, qid, text, use_llm: useLlm }),

  // T-231 — 인터뷰 확정 화면용 성향 프리뷰(순수, 게임 미생성).
  clonePreview: (answers: Record<string, number>) =>
    post<{ status: string; trap_scores: Record<string, number>;
          traits: { id: string; name: string; score: number }[] }>(
      "/control/clone/preview", { answers }),

  // -- 게임 세션 --
  gameStart: (
    gameId: string, answers: Record<string, number>, symbol: string, startPrice = 100.0,
    allocations?: Record<string, number>, village = "balanced",   // T-273
  ) =>
    post<{ status: string; state: GameState }>(
      "/control/game/start",
      { game_id: gameId, answers, symbol, start_price: startPrice,
        allocations: allocations ?? null, village }),
  gameState: (gameId: string) =>
    get<{ status: string; state: GameState }>("/control/game/state", { game_id: gameId }),
  gamePreview: (gameId: string) =>
    get<{ status: string; slots: unknown[]; schedule: Record<string, string>; meetings: Meetings; picks: Picks; designated: Designated }>(
      "/control/game/day/preview", { game_id: gameId }),
  gameAvoid: (gameId: string, slotA: number, slotB: number) =>
    post<{ status: string; schedule: Record<string, string>; meetings: Meetings }>(
      "/control/game/day/avoid", { game_id: gameId, slot_a: slotA, slot_b: slotB }),
  // T-272a — 대화 상대 지정(npc_id=null이면 해제=클론에게 맡김). 자연 멱등.
  gameDesignate: (gameId: string, slot: number, npcId: string | null) =>
    post<{ status: string; meetings: Meetings; picks: Picks; designated: Designated }>(
      "/control/game/day/designate", { game_id: gameId, slot, npc_id: npcId }),
  // T-272b — 행선지 지정(스왑 등가 — 재전송 no-op 자연 멱등).
  gameRelocate: (gameId: string, slot: number, place: string) =>
    post<{ status: string; schedule: Record<string, string>; meetings: Meetings; picks: Picks; designated: Designated }>(
      "/control/game/day/relocate", { game_id: gameId, slot, place }),
  // T-271 — 긴급 속보 사이렌: 오늘 활성 여부 조회(GET, 무변이) + 선택(POST, 자연 멱등).
  // T-288 — 메신저 대화방: NPC별 일자별 대화 로그(만남 대사+권유 요약). 순수 조회.
  gameChatLog: (gameId: string, npcId: string) =>
    get<{ status: string; npc_id: string; days: ChatLogDay[] }>(
      "/control/game/chat_log", { game_id: gameId, npc_id: npcId }),
  gameSiren: (gameId: string) =>
    get<{ status: string; day: number; active: boolean; used: boolean }>(
      "/control/game/day/siren", { game_id: gameId }),
  gameSirenChoose: (gameId: string, day: number, choice: "bad" | "good" | "skip") =>
    post<{ status: string; applied?: boolean; duplicate?: boolean; kind?: string;
          stat?: string | null; stat_delta?: number; crowd_delta?: number }>(
      "/control/game/day/siren", { game_id: gameId, day, choice }),
  // T-269 — 발자취(일별 뉴스 선택·만남·소셜·일과). 순수 조회.
  gameHistory: (gameId: string) =>
    get<{ status: string; run_id: string; days: HistoryDay[] }>(
      "/control/game/history", { game_id: gameId }),
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
  // T-256 — 그날 매매 순간(클론 fund_flow + NPC 판정). 순수 조회.
  gameTrades: (gameId: string, day?: number) =>
    get<{ status: string; day: number;
         trades: { id: string; name: string; action: "buy" | "sell" }[] }>(
      "/control/game/day/trades",
      day === undefined ? { game_id: gameId } : { game_id: gameId, day: String(day) }),
  // T-245 §13.7 — 마을 수익률 순위(배경 정보 톤).
  gameLeaderboard: (gameId: string) =>
    get<{ status: string; board: { id: string; name: string; return_pct: number }[];
         clone_rank: number; total: number }>(
      "/control/game/leaderboard", { game_id: gameId }),
  gameBoard: (gameId: string, useLlm = false) =>
    get<{ status: string } & BoardFeed>("/control/game/day/board", { game_id: gameId, use_llm: useLlm }),
  gameCrisisCheck: (gameId: string, newsId?: string) =>
    get<{ status: string; trap: string | null; trap_name: string | null;
         bundle: { category: string; trap: string; trap_name: string }[] }>(
      "/control/game/day/crisis_check", { game_id: gameId, news_id: newsId }),
  gameAdvance: (gameId: string, opts: { newsId?: string; strategy?: string; rapport?: number; roll?: number; idemKey?: string } = {}) =>
    // T-265 — 멱등성 키 덕에 이 POST만 재시도 1회 허용(fetchJson 3번째 인자):
    // 응답이 유실돼도 서버가 같은 키를 캐시 응답으로 받아쳐 하루 이중 진행이 없다.
    // /review 정정 — 키는 호출자가 (run,day)에서 파생해 넘긴다: 매 호출 랜덤이면
    // 에러 배너 후 사용자의 수동 재시도가 새 키가 되어 이중 적용을 못 막는다.
    fetchJson<{ status: string; state: GameState; day_result?: DayResult; card?: ResultCard }>(
      "/control/game/day/advance", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          game_id: gameId, news_id: opts.newsId ?? null, strategy: opts.strategy ?? null,
          // rapport를 null로 보내면 백엔드가 GameRun의 실제 공유 래포 풀을 쓴다
          // (opts.rapport를 넘기지 않는 게 일반 플레이의 기본 경로).
          rapport: opts.rapport ?? null, roll: opts.roll ?? Math.random() * 100,
          idem_key: opts.idemKey
            ?? `adv-${gameId}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        }),
      }, 1),
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
    // T-c — npc_rapport/npc_line: NPC별 래포·기억 반영 응답(구 서버 호환 optional).
    post<{ status: string; accepted: boolean; success_prob: number; rapport: number;
           npc_rapport?: number; npc_line?: string }>(
      "/control/game/social/persuade", { game_id: gameId, npc_id: npcId, direction, roll }),
  fgi: (gameId: string, tone: string, roll = 20.0) =>
    post<{ status: string; crowd_mood: number; clone_delta_applied: number; absorbed: boolean }>(
      "/control/game/social/fgi", { game_id: gameId, tone, roll }),
};

export const STAT_LABELS: (keyof CloneStats)[] = [
  "급락패닉저항", "멘탈마모저항", "익절거부제어", "과대베팅제어", "추격매수저항", "막차불안저항", "멘탈회복",
];
