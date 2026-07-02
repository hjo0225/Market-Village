"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import PixelButton from "@/components/pixel/PixelButton";
import PixelModal from "@/components/pixel/PixelModal";
import StatsPanel from "@/components/StatsPanel";
import PhoneModal from "@/components/PhoneModal";
import PreviewModal from "@/components/PreviewModal";
import NewsModal from "@/components/NewsModal";
import DayResultToast from "@/components/DayResultToast";
import BoardEventModal from "@/components/BoardEventModal";
import CrisisEventModal from "@/components/CrisisEventModal";
import DayProgressOverlay from "@/components/DayProgressOverlay";
import MapBackground, { MapBackgroundHandle } from "@/components/MapBackground";
import { api, BoardFeed, GameState, NewsItem, Meetings, Picks, DayResult } from "@/lib/api";
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
  const [schedule, setSchedule] = useState<Record<string, string>>({});
  const [newsId, setNewsId] = useState<string | null>(null);
  const [phoneOpen, setPhoneOpen] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [newsOpen, setNewsOpen] = useState(false);
  const [statsOpen, setStatsOpen] = useState(false);
  const [advancing, setAdvancing] = useState(false);
  const [dayResult, setDayResult] = useState<DayResult | null>(null);
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
    const [st, prev, nw] = await Promise.all([
      api.gameState(id), api.gamePreview(id), api.gameNews(id),
    ]);
    // 프록시 네트워크 플레이크(fetchJson이 재시도 후에도 실패)로 status가
    // "ok"가 아니면 화면을 깨뜨리지 말고 기존 상태를 유지 — 다음 진행/재시도 때
    // 다시 채워진다.
    if (st.status !== "ok") return;
    setState(st.state);
    if (prev.status === "ok") {
      setMeetings(prev.meetings); setPicks(prev.picks);
      setSchedule(prev.schedule ?? {});   // T-240 — 진행 중 일정 안내에 사용
    }
    if (nw.status === "ok") setNews(nw.news);
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
      setBoardFeed(board);
      await new Promise<void>((resolve) => { boardCloseResolver.current = resolve; });
      setBoardFeed(null);
      boardCloseResolver.current = null;
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
    await Promise.all([sleep(DAY_STAGE_MS / speedRef.current), mapRef.current?.playWalk("오후", speedRef.current) ?? sleep(0)]);
    setDayStage(3);           // 🌇 저녁
    await Promise.all([sleep(DAY_STAGE_MS / speedRef.current), mapRef.current?.playWalk("저녁", speedRef.current) ?? sleep(0)]);
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
      });
      // 걷기는 각 시간대 단계에서 이미 동기 재생됐다(T-237) — 여기선 대기 불필요.
      if (r.day_result) setDayResult(r.day_result);
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
          <h1 className="text-lg font-extrabold">🪞 {state.run_id}</h1>
          <span className="text-sm">Day <b>{state.day}</b>/{state.days}</span>
          <span className="text-sm">총자산 <b>{Math.round(state.total_asset)}</b></span>
          {/* T-245 — 마을 순위(배경 정보 톤, 버튼 아님 — 목표는 순위가 아니라 카드 등급 §13.7) */}
          {rank && (
            <span className="text-xs text-pixel-muted">
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
        meetings={meetings} picks={picks} onChanged={() => refresh(gameId)}
      />
      <DayResultToast result={dayResult} scene={sceneText} />
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
