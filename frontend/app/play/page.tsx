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
import CrisisEventModal from "@/components/CrisisEventModal";
import DayProgressOverlay from "@/components/DayProgressOverlay";
import MapBackground, { MapBackgroundHandle } from "@/components/MapBackground";
import { api, GameState, NewsItem, Meetings, Picks, DayResult } from "@/lib/api";
import { getGameId } from "@/lib/session";

// 사용자 피드백(2026-07-01) — "하루가 2분동안 진행되는 속도로". 3단계(아침·한낮·
// 저녁) × 20초 = 60초 연출 + 실제 지도 걷기(~50초, map.html에서 조정) ≈ 총 2분.
const DAY_STAGE_MS = 20000;
const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export default function PlayPage() {
  const router = useRouter();
  const mapRef = useRef<MapBackgroundHandle>(null);
  const [gameId, setGid] = useState<string | null>(null);
  const [state, setState] = useState<GameState | null>(null);
  const [news, setNews] = useState<NewsItem[]>([]);
  const [meetings, setMeetings] = useState<Meetings>({});
  const [picks, setPicks] = useState<Picks>({});
  const [newsId, setNewsId] = useState<string | null>(null);
  const [phoneOpen, setPhoneOpen] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [newsOpen, setNewsOpen] = useState(false);
  const [statsOpen, setStatsOpen] = useState(false);
  const [advancing, setAdvancing] = useState(false);
  const [dayResult, setDayResult] = useState<DayResult | null>(null);
  const [sceneText, setSceneText] = useState("");
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
      api.gameState(id), api.gamePreview(id), api.gameNews(id, 0),
    ]);
    // 프록시 네트워크 플레이크(fetchJson이 재시도 후에도 실패)로 status가
    // "ok"가 아니면 화면을 깨뜨리지 말고 기존 상태를 유지 — 다음 진행/재시도 때
    // 다시 채워진다.
    if (st.status !== "ok") return;
    setState(st.state);
    if (prev.status === "ok") { setMeetings(prev.meetings); setPicks(prev.picks); }
    if (nw.status === "ok") setNews(nw.news);
    if (st.state.finished) router.replace("/report");
  }, [router]);

  useEffect(() => {
    if (gameId) refresh(gameId);
  }, [gameId, refresh]);

  // "하루 진행" 클릭 — 사용자 피드백(2026-07-01): 하루가 순간이동처럼 느껴지지
  // 않게 2분 가량에 걸쳐 아침→한낮→저녁 순으로 흘러간다. 위기가 실제 발생한
  // 날이면(시장조건만으로 결정, 뉴스/개입과 무관하므로 미리 조용히 조회해도
  // 결과가 달라지지 않음) 그 흐름을 멈추고 이벤트 모달을 띄워 선택을 기다린다.
  async function handleAdvance() {
    if (!gameId || advancing) return;
    setAdvancing(true);
    setDayResult(null); setSceneText("");
    const checkPromise = api.gameCrisisCheck(gameId, newsId ?? undefined);

    setDayStage(0);           // 🌅 아침
    await sleep(DAY_STAGE_MS);
    setDayStage(1);           // ☀️ 한낮 — 위기가 있다면 여기서 멈춘다
    const check = await checkPromise;
    if (check.status === "ok" && check.trap && check.trap_name) {
      setDayStage(-1);
      setCrisisTrapName(check.trap_name);
      setCrisisBundle(check.bundle ?? []);
      return;   // 실제 진행은 모달의 선택(handleCrisisChoice)에서 이어진다.
    }
    await sleep(DAY_STAGE_MS);
    setDayStage(2);           // 🌇 저녁
    await sleep(DAY_STAGE_MS);
    await finishAdvance(null);
  }

  async function handleCrisisChoice(strategy: string | null) {
    if (crisisChoosing) return;   // 중복 클릭 방지
    setCrisisChoosing(true);
    setCrisisTrapName(null);
    setCrisisBundle([]);
    setDayStage(2);           // 🌇 선택 후 저녁으로 이어서 진행
    await sleep(DAY_STAGE_MS);
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
        newsId: newsId ?? undefined,
        strategy: strategy || undefined,
        roll: Math.random() * 100,
      });
      // 배경 지도가 오늘 하루를 실제로 다 걸을 때까지 기다린 뒤에야 결과를
      // 드러낸다(T-FE2) — 안 그러면 화면이 순간이동처럼 느껴진다(사용자 피드백).
      await mapRef.current?.playWalk();
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
          <div className="flex-1" />
          <PixelButton size="sm" variant="secondary" onClick={() => setStatsOpen(true)}>📊 상태</PixelButton>
          <PixelButton
            size="sm" variant={newsId ? "primary" : "secondary"}
            onClick={() => setNewsOpen(true)}
          >📰 뉴스{newsId ? " ✓" : ""}</PixelButton>
          <PixelButton size="sm" variant="secondary" onClick={() => setPreviewOpen(true)}>🌙 전날밤</PixelButton>
          <PixelButton size="sm" variant="secondary" onClick={() => setPhoneOpen(true)}>📱 핸드폰</PixelButton>
        </header>
      </div>

      <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-10">
        <PixelButton size="lg" disabled={advancing} onClick={handleAdvance}>
          {advancing ? "진행 중…" : "하루 진행 ▶"}
        </PixelButton>
      </div>

      <DayProgressOverlay stageIndex={dayStage} />

      <PixelModal isOpen={statsOpen} onClose={() => setStatsOpen(false)} title="🪞 클론 상태" size="sm">
        <StatsPanel stats={state.stats} portfolio={state.portfolio} showTitle={false} />
      </PixelModal>
      <NewsModal
        isOpen={newsOpen} onClose={() => setNewsOpen(false)} news={news}
        onSelect={(id) => setNewsId(id)}
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
      {crisisTrapName && (
        <CrisisEventModal
          trapName={crisisTrapName} bundle={crisisBundle}
          busy={crisisChoosing} onChoose={handleCrisisChoice}
        />
      )}
    </main>
  );
}
