"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import PixelButton from "@/components/pixel/PixelButton";
import PixelModal from "@/components/pixel/PixelModal";
import StatsPanel from "@/components/StatsPanel";
import PhoneModal from "@/components/PhoneModal";
import PreviewModal from "@/components/PreviewModal";
import NewsModal from "@/components/NewsModal";
import DayResultModal from "@/components/DayResultModal";
import BoardEventModal from "@/components/BoardEventModal";
import CrisisEventModal from "@/components/CrisisEventModal";
import DayProgressOverlay from "@/components/DayProgressOverlay";
import MapBackground, { MapBackgroundHandle } from "@/components/MapBackground";
import { api, BoardFeed, Designated, GameState, HistoryDay, NewsItem, Meetings, Picks, DayResult } from "@/lib/api";
import HistoryPanel from "@/components/HistoryPanel";
import SirenEventModal from "@/components/SirenEventModal";
import { getGameId } from "@/lib/session";

// 사용자 피드백(2026-07-01) — "하루가 2분동안 진행되는 속도로". 4단계 × 20초 기본.
// T-243(council M1) — §13.3 빨리감기: 배속(1×/2×/4×)이 스테이지·걷기에 함께 적용.
const DAY_STAGE_MS = 20000;
const SPEED_OPTIONS = [1, 2, 4];
const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export default function PlayPage() {
  const router = useRouter();
  const mapRef = useRef<MapBackgroundHandle>(null);
  const [gameId, setGid] = useState<string | null>(null);
  const [state, setState] = useState<GameState | null>(null);
  const [news, setNews] = useState<NewsItem[]>([]);
  const [meetings, setMeetings] = useState<Meetings>({});
  const [picks, setPicks] = useState<Picks>({});
  const [designated, setDesignated] = useState<Designated>({});   // T-272a
  const [history, setHistory] = useState<HistoryDay[]>([]);       // T-269 발자취
  // T-271 — 긴급 속보 사이렌: 오후 스테이지에 한시(20초/배속) 등장, 놓치면 소멸.
  const [sirenVisible, setSirenVisible] = useState(false);
  const [sirenModalOpen, setSirenModalOpen] = useState(false);
  const [sirenBusy, setSirenBusy] = useState(false);
  const [sirenToast, setSirenToast] = useState<string | null>(null);
  const sirenTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [schedule, setSchedule] = useState<Record<string, string>>({});
  const [newsId, setNewsId] = useState<string | null>(null);
  const [phoneOpen, setPhoneOpen] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [newsOpen, setNewsOpen] = useState(false);
  const [statsOpen, setStatsOpen] = useState(false);
  const [advancing, setAdvancing] = useState(false);
  const [dayResult, setDayResult] = useState<DayResult | null>(null);
  // /review — 모달이 열리는 시점의 state.day는 refresh 전이라 하루 늦다:
  // 서버 응답(r.state.day, 진행 후 값)에서 파생해 라벨 점프를 없앤다.
  const [resultDay, setResultDay] = useState(0);
  const [advanceError, setAdvanceError] = useState<string | null>(null);   // T-265
  const [sceneText, setSceneText] = useState("");
  // 게시판(T-225, D1·D3) — 이벤트 날 아침 뒤에만 뜨는 블로킹 관찰 이벤트.
  // 닫기 전엔 하루가 진행되지 않는다(resolver로 진행 재개).
  const [boardFeed, setBoardFeed] = useState<BoardFeed | null>(null);
  const boardCloseResolver = useRef<(() => void) | null>(null);
  // T-234 — 하루진행이 뉴스 선택을 기다리는 중인가(모달에서 선택/스킵 시 진행 시작).
  const [pendingAdvance, setPendingAdvance] = useState(false);
  const chosenNewsRef = useRef<string | null>(null);
  // T-243 — 하루 배속(스테이지·걷기 연동). 모달(뉴스·게시판·위기)은 배속 무관.
  const [speed, setSpeed] = useState(1);
  const speedRef = useRef(1);
  speedRef.current = speed;
  // T-245 §13.7 — 마을 수익률 순위(배경 정보 톤 — 목표는 순위가 아니라 카드 등급).
  const [rank, setRank] = useState<{ rank: number; total: number; delta: number } | null>(null);
  const prevRankRef = useRef<number | null>(null);
  // 위기가 실제 발생했을 때만 뜨는 이벤트 — 평소엔 null(상시 노출 안 함).
  const [crisisTrapName, setCrisisTrapName] = useState<string | null>(null);
  // T-216 D4 — 같은 날 2종목 이상 트리거되면 여기 전부 담김(1개면 길이 1).
  const [crisisBundle, setCrisisBundle] = useState<{ category: string; trap: string; trap_name: string }[]>([]);
  // 선택 처리 중(중복 클릭 방지)만 true — advancing과 분리해야 한다. advancing은
  // 모달이 떠 있는 동안(사용자 응답 대기 중)에도 계속 true라, 그걸 그대로 버튼
  // disabled에 쓰면 선택 버튼 자체가 눌리지 않는 회귀 버그가 난다.
  const [crisisChoosing, setCrisisChoosing] = useState(false);
  // "하루가 흐르는" 연출 단계(-1=꺼짐, 0~2=아침/한낮/저녁). 위기 모달이 뜨면
  // 이 연출은 멈춘다(둘 다 안 보여줌 — CrisisEventModal이 우선).
  const [dayStage, setDayStage] = useState(-1);

  useEffect(() => {
    const id = getGameId();
    if (!id) { router.replace("/setup"); return; }
    setGid(id);
  }, [router]);

  const refresh = useCallback(async (id: string) => {
    const [st, prev, nw, hist] = await Promise.all([
      api.gameState(id), api.gamePreview(id), api.gameNews(id), api.gameHistory(id),
    ]);
    // 프록시 네트워크 플레이크(fetchJson이 재시도 후에도 실패)로 status가
    // "ok"가 아니면 화면을 깨뜨리지 말고 기존 상태를 유지 — 다음 진행/재시도 때
    // 다시 채워진다.
    if (st.status !== "ok") return;
    setState(st.state);
    if (prev.status === "ok") {
      setMeetings(prev.meetings); setPicks(prev.picks);
      setDesignated(prev.designated ?? {});   // T-272a — 구서버 응답엔 없음 → {}
      setSchedule(prev.schedule ?? {});   // T-240 — 진행 중 일정 안내에 사용
    }
    if (nw.status === "ok") setNews(nw.news);
    if (hist.status === "ok") setHistory(hist.days);   // T-269
    // T-245 — 마을 순위(실패해도 화면 안 깨짐 — 칩만 안 뜸).
    const lb = await api.gameLeaderboard(id);
    if (lb.status === "ok") {
      const delta = prevRankRef.current === null ? 0 : prevRankRef.current - lb.clone_rank;
      prevRankRef.current = lb.clone_rank;
      setRank({ rank: lb.clone_rank, total: lb.total, delta });
    }
    if (st.state.finished) router.replace("/report");
  }, [router]);

  useEffect(() => {
    if (gameId) refresh(gameId);
  }, [gameId, refresh]);

  // "하루 진행" 클릭 — 사용자 피드백(2026-07-01): 하루가 순간이동처럼 느껴지지
  // 않게 2분 가량에 걸쳐 아침→한낮→저녁 순으로 흘러간다. 위기가 실제 발생한
  // 날이면(시장조건만으로 결정, 뉴스/개입과 무관하므로 미리 조용히 조회해도
  // 결과가 달라지지 않음) 그 흐름을 멈추고 이벤트 모달을 띄워 선택을 기다린다.
  function handleAdvance() {
    if (!gameId || advancing) return;
    // T-234(§7.4 매일 아침 3지선다) — 아직 뉴스를 안 골랐으면 선택부터. 헤더 📰로
    // 미리 골라뒀으면 바로 진행. 모달에서 선택/스킵하면 이어서 진행된다.
    if (!newsId) { setPendingAdvance(true); setNewsOpen(true); return; }
    void runAdvance(newsId);
  }

  async function runAdvance(chosenNewsId: string | null) {
    if (!gameId || advancing) return;
    chosenNewsRef.current = chosenNewsId;   // 위기 선택 경로(finishAdvance)도 같은 뉴스 사용
    setAdvancing(true);
    setDayResult(null); setSceneText("");
    const checkPromise = api.gameCrisisCheck(gameId, chosenNewsId ?? undefined);
    // T-225(D3) — 게시판 판정도 아침 단계에서 미리 조회. 부작용 없는 판정 재사용
    // (백엔드가 위기 프리뷰+그날 뽑힌 뉴스로 열림 여부를 정함, 같은 날 재호출=캐시).
    const boardPromise = api.gameBoard(gameId);

    // T-237(§12.1b) — 하루 8슬롯 = 4시간대(오전2·점심2·오후2·저녁2). 각 단계에서
    // 그 시간대 일과 구간을 걷는다(단계 길이 = max(연출 최소시간, 그 구간 걷기)).
    setDayStage(0);           // 🌅 오전
    await Promise.all([sleep(DAY_STAGE_MS / speedRef.current), mapRef.current?.playWalk("오전", speedRef.current) ?? sleep(0)]);
    // 이벤트 있는 날이면 📱 게시판(블로킹) — 닫을 때까지 하루가 멈춘다(D1·D3).
    const board = await boardPromise;
    if (board.status === "ok" && board.open) {
      setDayStage(-1);
      // T-255 — 마을 전체가 걸음을 멈추고 핸드폰 알림(❗)이 뜬 뒤 피드가 올라온다.
      mapRef.current?.signal({ type: "board_gather" });
      await sleep(900);
      setBoardFeed(board);
      await new Promise<void>((resolve) => { boardCloseResolver.current = resolve; });
      setBoardFeed(null);
      boardCloseResolver.current = null;
      mapRef.current?.signal({ type: "board_release" });
    }
    setDayStage(1);           // 🍜 점심 — 끝나면 위기 판정(오후 장 직전)
    await Promise.all([sleep(DAY_STAGE_MS / speedRef.current), mapRef.current?.playWalk("점심", speedRef.current) ?? sleep(0)]);
    const check = await checkPromise;
    if (check.status === "ok" && check.trap && check.trap_name) {
      setDayStage(-1);
      setCrisisTrapName(check.trap_name);
      setCrisisBundle(check.bundle ?? []);
      return;   // 실제 진행은 모달의 선택(handleCrisisChoice)에서 이어진다.
    }
    await playAfternoonEvening();
    await finishAdvance(null);
  }

  // 오후·저녁 구간(위기 유무와 무관한 하루의 꼬리) — 위기 선택 후에도 재사용.
  async function playAfternoonEvening() {
    setDayStage(2);           // ☀️ 오후
    void maybeShowSiren();    // T-271 — 오후 장에 사이렌(뜨는 날만, 놓치면 소멸)
    await Promise.all([sleep(DAY_STAGE_MS / speedRef.current), mapRef.current?.playWalk("오후", speedRef.current) ?? sleep(0)]);
    setDayStage(3);           // 🌇 저녁
    await Promise.all([sleep(DAY_STAGE_MS / speedRef.current), mapRef.current?.playWalk("저녁", speedRef.current) ?? sleep(0)]);
    // T-271 — 사이렌 창은 하루의 꼬리에서 정리(선택 모달이 열려 있으면 그대로 두고,
    // 밤 정산(finishAdvance)에서 stale day가 자연 차단한다).
    if (sirenTimerRef.current) clearTimeout(sirenTimerRef.current);
    setSirenVisible(false);
  }

  // T-271 — 사이렌 판정(GET, 무변이): 뜨는 날 + 미소비면 20초(배속 반영) 창을 연다.
  async function maybeShowSiren() {
    if (!gameId) return;
    const s = await api.gameSiren(gameId);
    if (s.status !== "ok" || !s.active || s.used) return;
    setSirenVisible(true);
    if (sirenTimerRef.current) clearTimeout(sirenTimerRef.current);
    sirenTimerRef.current = setTimeout(
      () => setSirenVisible(false), 20000 / speedRef.current);
  }

  async function handleSirenChoose(choice: "bad" | "good" | "skip") {
    if (!gameId || !state || sirenBusy) return;
    setSirenBusy(true);
    try {
      const r = await api.gameSirenChoose(gameId, state.day, choice);
      if (r.status === "ok" && r.applied) {
        setSirenToast(
          choice === "bad" ? `🚨 갑작스런 악재가 퍼졌다 — 마을이 술렁인다 (저항 ${r.stat_delta})`
          : choice === "good" ? `🚨 갑작스런 호재가 퍼졌다 — 마을이 들뜬다 (저항 ${r.stat_delta})`
          : "🤫 이번 속보는 조용히 넘겼다.");
      } else if (r.status !== "ok") {
        setSirenToast("속보가 이미 지나갔어요.");
      }
      setTimeout(() => setSirenToast(null), 4000);
      setSirenModalOpen(false);
      setSirenVisible(false);
      await refresh(gameId);
    } finally {
      setSirenBusy(false);
    }
  }

  async function handleCrisisChoice(strategy: string | null) {
    if (crisisChoosing) return;   // 중복 클릭 방지
    setCrisisChoosing(true);
    setCrisisTrapName(null);
    setCrisisBundle([]);
    await playAfternoonEvening();   // 선택 후 오후→저녁으로 이어서 진행
    await finishAdvance(strategy);
    setCrisisChoosing(false);
  }

  async function finishAdvance(strategy: string | null) {
    if (!gameId) { setAdvancing(false); setDayStage(-1); return; }
    try {
      // rapport는 안 보낸다 — 백엔드가 GameRun의 실제 공유 래포 풀(1:1 대화로
      // 쌓인 값)을 자동으로 쓴다. roll은 매번 진짜 난수(고정값을 쓰면 위기개입이
      // 결정론적으로 항상 같은 결과만 나온다 — 사용자 피드백 2026-07-01).
      const r = await api.gameAdvance(gameId, {
        newsId: chosenNewsRef.current ?? undefined,
        strategy: strategy || undefined,
        roll: Math.random() * 100,
        // T-265(/review) — 키는 (run,day) 파생: 자동 재시도든 에러 배너 후
        // 수동 재클릭이든 같은 날엔 같은 키 → 서버가 이중 적용을 막는다.
        // (state가 아직 없으면 랜덤 폴백 — api.gameAdvance 기본 생성 사용)
        idemKey: state ? `adv-${gameId}-${state.run_id}-d${state.day}` : undefined,
      });
      // T-265 — 재시도(멱등키)까지 실패한 극단 케이스: 침묵하지 않는다(QA 스윕
      // Day12 실측 — 조용히 하루가 밀리면 사용자는 원인을 알 수 없다).
      if (r.status !== "ok") {
        setAdvanceError("네트워크가 불안정해 하루 진행이 반영되지 않았어요. 다시 눌러주세요.");
        return;
      }
      setAdvanceError(null);
      // 걷기는 각 시간대 단계에서 이미 동기 재생됐다(T-237) — 여기선 대기 불필요.
      if (r.day_result) { setResultDay(Math.max(0, r.state.day - 1)); setDayResult(r.day_result); }
      // T-256 — 오늘 사고판 이들(클론 fund_flow + NPC 판정)을 맵에서 💸/📉로.
      const tr = await api.gameTrades(gameId);
      if (tr.status === "ok" && tr.trades.length) {
        mapRef.current?.signal({ type: "trade_fx", trades: tr.trades });
      }
      // T-SVC8 테스트: 실LLM으로 클론 대사 표현만 다듬는다(수치 결정 무관, 실패 시 템플릿 폴백).
      const scene = await api.gameScene(gameId, true);
      if (scene.status === "ok" && scene.scene) setSceneText(scene.scene.dialogue);
      setNewsId(null);
      await refresh(gameId);
    } finally {
      setAdvancing(false);
      setDayStage(-1);
    }
  }

  // T-240 — 지금 시간대(스테이지)의 일정 문구: 슬롯 1·2=오전 … 7·8=저녁(§12.1b).
  const PLACE_ICONS: Record<string, string> = {
    카페: "☕", 일터: "🛠", 광장: "🌳", 운동: "🏃", "집_차트": "🏠",
    펍: "🍺", 마켓: "🧺", 도서관: "📚",
  };
  const PLACE_NAMES: Record<string, string> = { "집_차트": "집(차트 보기)" };
  const BAND_SLOTS = [[1, 2], [3, 4], [5, 6], [7, 8]];
  const stagePlan = dayStage >= 0 && dayStage < BAND_SLOTS.length
    ? BAND_SLOTS[dayStage]
        .map((s) => schedule[String(s)])
        .filter(Boolean)
        .map((p) => `${PLACE_ICONS[p] ?? "📍"} ${PLACE_NAMES[p] ?? p}`)
        .join(" → ")
    : undefined;

  if (!gameId || !state) {
    return <main className="min-h-screen flex items-center justify-center text-pixel-muted">불러오는 중…</main>;
  }

  return (
    <main className="min-h-screen relative">
      <MapBackground ref={mapRef} gameId={gameId} />

      {/* 사용자 피드백(2026-07-01) — 스탯·뉴스는 상시 패널이 아니라 이 리모콘의
          버튼 뒤로 숨긴다. 지도가 화면 대부분을 차지하게. */}
      <div className="relative z-10 p-5">
        <header className="flex items-center gap-4 mb-4 flex-wrap bg-white/90 backdrop-blur-sm border-2 border-black rounded-2xl shadow-pixel-md px-4 py-3">
          {/* T-266 — run_id는 내부 식별자라 비노출(사용자 피드백), 핵심 수치는 크게. */}
          <span className="text-base font-bold">🗓 Day <b className="text-xl">{state.day}</b><span className="text-pixel-muted">/{state.days}</span></span>
          <span className="text-base font-bold">💰 총자산 <b className="text-xl">{Math.round(state.total_asset)}</b></span>
          {/* T-245 — 마을 순위(배경 정보 톤, 버튼 아님 — 목표는 순위가 아니라 카드 등급 §13.7) */}
          {rank && (
            <span className="text-sm text-pixel-muted">
              🏘 마을 {rank.rank}위/{rank.total}
              {rank.delta > 0 && <b className="text-pixel-greenText"> ▲{rank.delta}</b>}
              {rank.delta < 0 && <b className="text-red-500"> ▼{-rank.delta}</b>}
            </span>
          )}
          <div className="flex-1" />
          <PixelButton size="sm" variant="secondary" onClick={() => setStatsOpen(true)}>📊 상태</PixelButton>
          <PixelButton
            size="sm" variant={newsId ? "primary" : "secondary"}
            onClick={() => setNewsOpen(true)}
          >📰 뉴스{newsId ? " ✓" : ""}</PixelButton>
          <PixelButton size="sm" variant="secondary" onClick={() => setPreviewOpen(true)}>🌙 전날밤</PixelButton>
          <PixelButton size="sm" variant="secondary" onClick={() => setPhoneOpen(true)}>📱 핸드폰</PixelButton>
          {/* T-243(§13.3 빨리감기) — 하루 연출 배속. 모달 선택 대기엔 영향 없음. */}
          <PixelButton
            size="sm" variant={speed > 1 ? "primary" : "ghost"}
            onClick={() => setSpeed(SPEED_OPTIONS[(SPEED_OPTIONS.indexOf(speed) + 1) % SPEED_OPTIONS.length])}
          >⏩ {speed}×</PixelButton>
        </header>
      </div>

      <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-10">
        <PixelButton size="lg" disabled={advancing} onClick={handleAdvance}>
          {advancing ? "진행 중…" : "하루 진행 ▶"}
        </PixelButton>
      </div>

      <DayProgressOverlay stageIndex={dayStage} plan={stagePlan} />

      {/* T-269 — 좌측 발자취 패널(오늘 일정+지금 이동 중+지난 날 이력) */}
      <HistoryPanel
        history={history} todaySchedule={schedule} today={state.day}
        heading={stagePlan ?? null}
      />

      <PixelModal isOpen={statsOpen} onClose={() => setStatsOpen(false)} title="🪞 클론 상태" size="sm">
        <StatsPanel stats={state.stats} portfolio={state.portfolio} showTitle={false} />
      </PixelModal>
      <NewsModal
        isOpen={newsOpen} news={news}
        onClose={() => { setNewsOpen(false); setPendingAdvance(false); }}
        onSelect={(id) => {
          setNewsId(id);
          // T-234 — 하루진행이 뉴스 선택을 기다리던 중이면 그 뉴스로 바로 진행.
          if (pendingAdvance) { setPendingAdvance(false); void runAdvance(id); }
        }}
        // T-247 ⑨ — 스킵 경로 제거: 뉴스 선택은 조작 변인의 핵심이라 필수.
        onSkip={undefined}
      />
      <PhoneModal
        isOpen={phoneOpen} onClose={() => setPhoneOpen(false)} gameId={gameId}
        rapport={state.rapport} crowdMood={state.crowd_mood}
        onChanged={() => refresh(gameId)}
      />
      <PreviewModal
        isOpen={previewOpen} onClose={() => setPreviewOpen(false)} gameId={gameId}
        meetings={meetings} picks={picks} designated={designated} schedule={schedule}
        onChanged={() => refresh(gameId)}
      />
      <DayResultModal
        result={dayResult} scene={sceneText} day={resultDay}
        onClose={() => setDayResult(null)}
      />
      {/* T-271 — 우하단 사이렌(한시 등장, 클릭=속보 선택) */}
      {sirenVisible && (
        <button
          onClick={() => setSirenModalOpen(true)}
          aria-label="긴급 속보"
          className="fixed bottom-6 right-6 z-[130] w-16 h-16 flex items-center justify-center
            text-3xl bg-white border-2 border-black rounded-2xl shadow-pixel-lg
            animate-pulse cursor-pointer hover:scale-110 transition-transform"
        >
          🚨
        </button>
      )}
      <SirenEventModal
        isOpen={sirenModalOpen} busy={sirenBusy}
        onChoose={(c) => void handleSirenChoose(c)}
        onClose={() => setSirenModalOpen(false)}
      />
      {sirenToast && (
        <div className="fixed bottom-24 right-6 z-[130] bg-white border-2 border-black rounded-xl shadow-pixel-md px-4 py-2 text-sm font-bold animate-slide-up">
          {sirenToast}
        </div>
      )}
      {advanceError && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-[125] bg-rose-50 border-2 border-black rounded-xl shadow-pixel-lg px-4 py-2 text-xs font-bold animate-slide-up">
          ⚠️ {advanceError}
        </div>
      )}
      {boardFeed && (
        <BoardEventModal
          day={boardFeed.day} board={boardFeed}
          onClose={() => boardCloseResolver.current?.()}
        />
      )}
      {crisisTrapName && (
        <CrisisEventModal
          trapName={crisisTrapName} bundle={crisisBundle}
          busy={crisisChoosing} onChoose={handleCrisisChoice}
        />
      )}
    </main>
  );
}
