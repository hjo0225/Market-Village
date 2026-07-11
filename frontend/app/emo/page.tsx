"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import * as api from "@/lib/emoApi";
import { Board, ChainEvent, Dilemma, EmoState, AXES, Axis, Emotion } from "@/lib/emoApi";
import AdvDialogue from "@/components/AdvDialogue";
import AdvChoiceMenu from "@/components/AdvChoiceMenu";
import DayReport, { DayReportData } from "@/components/DayReport";
import MapBackground, { MapBackgroundHandle } from "@/components/MapBackground";
import StoryScene from "@/components/StoryScene";
import DailyPlan from "@/components/DailyPlan";
import TickerBar from "@/components/TickerBar";
import CoachMark from "@/components/CoachMark";
import TitleScreen from "@/components/TitleScreen";
import OnboardingWizard from "@/components/emo/OnboardingWizard";
import EndingScreen from "@/components/emo/EndingScreen";
import PlayHeader from "@/components/emo/PlayHeader";
import BoardOpinionFeed from "@/components/emo/BoardOpinionFeed";
import CoinPicker from "@/components/emo/CoinPicker";
import PortfolioPopover from "@/components/emo/PortfolioPopover";
import TradeFlashBadge from "@/components/emo/TradeFlashBadge";
import { PlanView, CatalogCoin } from "@/lib/emoApi";
import { Level, LevelMap } from "@/types/emo";
import {
  PROLOGUE_CUTS, BRIDGE_CUTS, ENDING_PRE_CUT, FIRST_BOARD_CUT, HALFWAY_CUTS,
  DEFAULT_LEVELS, ALLOCATION_PRESET, QUESTIONS,
} from "@/constants/emo";
import { positionTag, levelWeights } from "@/utils/emo";

// 타이틀→온보딩→프롤로그→브릿지 내내 유지되는 단 하나의 컷씬 배경(Phaser).
// 화면 전환마다 iframe이 remount되며 재부팅(검은 반짝임)되던 것을 방지.
// src는 이름이 한 번 붙으면 고정(입력 중·화면 전환에 재로딩 없음).
function CutsceneBackdrop({ name }: { name: string }) {
  const srcRef = useRef("/map.html?mode=cutscene");
  if (name && !srcRef.current.includes("name=")) {
    srcRef.current = `/map.html?mode=cutscene&name=${encodeURIComponent(name)}`;
  }
  return (
    <div className="fixed inset-0 bg-black" aria-hidden>
      <iframe
        src={srcRef.current}
        title="마을 배경"
        className="h-full w-full border-0 pointer-events-none"
      />
    </div>
  );
}

export default function EmoPage() {
  const [state, setState] = useState<EmoState | null>(null);
  const [board, setBoard] = useState<Board | null>(null);
  const [boardStep, setBoardStep] = useState(0);
  const [chain, setChain] = useState<ChainEvent | null>(null);
  const [dilemma, setDilemma] = useState<Dilemma | null>(null);
  const dilemmaPickRef = useRef<((id: string) => void) | null>(null);
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [questionIndex, setQuestionIndex] = useState(0);
  const [diagnosis, setDiagnosis] = useState<api.DispositionDiagnosis | null>(null);
  const [shareCopied, setShareCopied] = useState(false);
  const [name, setName] = useState("");
  const [levels, setLevels] = useState<LevelMap>({ ...DEFAULT_LEVELS });
  // T-65 (5안) — 배분이 성향 프리셋 상태인지 유저가 직접 손댔는지. "user"면 프리셋 재적용 안 함.
  const [allocSource, setAllocSource] = useState<"preset" | "user">("preset");
  const [step, setStep] = useState(0);
  const [screen, setScreen] = useState<"title" | "game">("title");
  const [seed, setSeed] = useState<number | null>(null);
  const [catalog, setCatalog] = useState<CatalogCoin[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showPortfolio, setShowPortfolio] = useState(false);
  const [flashAxis, setFlashAxis] = useState<Axis | null>(null);
  const [tradeFlash, setTradeFlash] = useState<{ action: "buy" | "sell"; detail?: string } | null>(null);
  const tradeFlashTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const prevEmoRef = useRef<Emotion | null>(null);
  const prevTierNameRef = useRef<string | null>(null);
  const [tierToast, setTierToast] = useState<string | null>(null);
  const tierToastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [dayReport, setDayReport] = useState<DayReportData | null>(null);
  const dayLogRef = useRef<{ label: string; tag: "buy" | "sell" | "hold" }[]>([]);
  const [report, setReport] = useState<api.DiagnosisReport | null>(null);
  const pendingNextRef = useRef<EmoState | null>(null);
  const mapRef = useRef<MapBackgroundHandle>(null);
  const stateRef = useRef<EmoState | null>(null);
  const boardPickRef = useRef<((v: { id: string; coin_target: string | null }) => void) | null>(null);
  const [coinPick, setCoinPick] = useState<{ action: string; choiceId: string } | null>(null);
  const day = state?.day ?? -1;

  const [storyScene, setStoryScene] = useState<"prologue" | "bridge" | "endingPre" | "firstBoard" | "halfway" | null>(null);
  const [endingCutDone, setEndingCutDone] = useState(false);
  const pendingStartRef = useRef<EmoState | null>(null);
  const firstBoardSeenRef = useRef(false);
  const halfwaySeenRef = useRef(false);
  const storySceneGateRef = useRef<(() => void) | null>(null);

  const [planView, setPlanView] = useState<PlanView | null>(null);
  const planGateRef = useRef<(() => void) | null>(null);
  const [planBusy, setPlanBusy] = useState(false);

  const setRun = useCallback((s: EmoState) => { stateRef.current = s; setState(s); }, []);
  const selectQuestionOption = useCallback((optionIndex: number) => {
    const q = QUESTIONS[questionIndex];
    const choice = q.options[optionIndex];
    if (!choice) return false;
    setAnswers((a) => ({ ...a, [q.key]: choice[1] }));
    setShareCopied(false);
    return true;
  }, [questionIndex]);
  const advanceQuestion = useCallback(() => {
    const q = QUESTIONS[questionIndex];
    if (!(q.key in answers)) return false;
    if (questionIndex < QUESTIONS.length - 1) setQuestionIndex((i) => i + 1);
    else setStep(2);
    return true;
  }, [answers, questionIndex]);

  // 하루 일과 시퀀스: 반환점 컷 → 일과 편성 게이트 → 캐시아웃 딜레마 → 4밴드 걷기
  // (점심=게시판 반응만 수집) → 저녁 정산(choose) → 정산 리포트.
  useEffect(() => {
    if (day < 0) return;
    let s = stateRef.current;
    if (!s || s.is_over) { setBoard(null); setChain(null); return; }
    let cancelled = false;
    (async () => {
      setBoard(null); setChain(null); setDilemma(null);
      dayLogRef.current = [];
      if (!halfwaySeenRef.current && s.total_days > 0 && s.day === Math.floor(s.total_days / 2)) {
        halfwaySeenRef.current = true;
        setStoryScene("halfway");
        await new Promise<void>((resolve) => { storySceneGateRef.current = resolve; });
        storySceneGateRef.current = null;
        setStoryScene(null);
        if (cancelled) return;
      }
      const pv = await api.getPlan(s.game_id);
      if (cancelled) return;
      if (pv && !pv.locked) {
        setPlanView(pv);
        await new Promise<void>((resolve) => { planGateRef.current = resolve; });
        planGateRef.current = null;
        setPlanView(null);
        s = stateRef.current ?? s;
      }
      if (cancelled) return;
      if (s.has_cashout_dilemma) {
        const dil = await api.getDilemma(s.game_id);
        if (dil && !cancelled) {
          setDilemma(dil);
          const cid = await new Promise<string>((resolve) => { dilemmaPickRef.current = resolve; });
          dilemmaPickRef.current = null;
          setDilemma(null);
          const dLabel = dil.choices.find((c) => c.id === cid)?.label ?? "";
          if (dLabel) dayLogRef.current.push({ label: dLabel, tag: cid === "cash_out" ? "sell" : "hold" });
          if (!cancelled) {
            const ns = await api.chooseDilemma(s.game_id, cid);
            if (ns && !cancelled) setRun(ns);
          }
        }
      }
      if (cancelled) return;
      const bands = ["오전", "점심", "오후", "저녁"];
      // 게시판 밴드는 점심 고정 — 오후 동행 만남과 겹치지 않게(순차 진행 보장).
      const boardBand = "점심";
      let picked: { id: string; coin_target: string | null } | null = null;
      let pickedLabel = "";
      for (const band of bands) {
        if (cancelled) return;
        await mapRef.current?.playWalk(band, 2);
        if (cancelled) return;
        if (band === boardBand) {
          if (!firstBoardSeenRef.current) {
            firstBoardSeenRef.current = true;
            setStoryScene("firstBoard");
            await new Promise<void>((resolve) => { storySceneGateRef.current = resolve; });
            storySceneGateRef.current = null;
            setStoryScene(null);
            if (cancelled) return;
          }
          const b = await api.getBoard(s.game_id);
          if (cancelled || !b) continue;
          setBoardStep(0);
          setBoard(b);
          picked = await new Promise<{ id: string; coin_target: string | null }>((resolve) => { boardPickRef.current = resolve; });
          boardPickRef.current = null;
          setCoinPick(null);
          const pickedChoice = b.scenario.choices.find((c) => c.id === picked!.id);
          pickedLabel = pickedChoice?.label ?? "";
          if (pickedLabel) {
            dayLogRef.current.push({ label: pickedLabel, tag: positionTag(pickedChoice?.position ?? 0) });
          }
          if (cancelled) return;
          setBoard(null);
        }
        const bandPlace = s.band_places?.[band];
        if ((band === "오전" || band === "저녁") && (bandPlace === "도서관" || bandPlace === "마켓")) {
          const pdil = await api.getPlaceDilemma(s.game_id, bandPlace);
          if (pdil && !cancelled) {
            setDilemma({ ...pdil, gain: false });
            const cid = await new Promise<string>((resolve) => { dilemmaPickRef.current = resolve; });
            dilemmaPickRef.current = null;
            setDilemma(null);
            const pLabel = pdil.choices.find((c) => c.id === cid)?.label ?? "";
            if (pLabel) {
              dayLogRef.current.push({ label: pLabel, tag: cid === "take_profit" || cid === "spend" ? "sell" : "hold" });
            }
            if (!cancelled) {
              const ns = await api.choosePlaceDilemma(s.game_id, bandPlace, cid);
              if (ns && !cancelled) setRun(ns);
            }
          }
        }
      }
      if (cancelled) return;
      if (picked) {
        const ns = await api.choose(s.game_id, picked.id, picked.coin_target);
        if (cancelled) return;
        if (!ns) { setError("정산에 실패했어요. 다시 시도해 주세요."); return; }
        if (ns.is_over) { setRun(ns); return; }
        const prev = stateRef.current ?? s;
        pendingNextRef.current = ns;
        setDayReport({
          day: prev.day, name: prev.clone_name,
          prevEmotion: prev.emotion, nextEmotion: ns.emotion,
          prevAsset: prev.portfolio_value, nextAsset: ns.portfolio_value,
          prevHoldings: prev.holdings, nextHoldings: ns.holdings,
          choiceLabel: pickedLabel,
          market: ns.last_market,
          log: dayLogRef.current,
          settlement: ns.settlement,
          prevTier: prev.tier, nextTier: ns.tier,
        });
      }
    })();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [day]);

  // 맵에서 클론이 동행에 도착(meeting_talk)하면 만남 카드를 연다.
  useEffect(() => {
    const onMsg = async (e: MessageEvent) => {
      if (e.data?.type !== "meeting_talk") return;
      mapRef.current?.signal({ type: "meeting_ack" });
      const s = stateRef.current;
      if (s && s.has_pending_chain) {
        const ch = await api.getChain(s.game_id);
        if (ch) { setChain(ch); return; }
      }
      mapRef.current?.signal({ type: "meeting_done" });
    };
    window.addEventListener("message", onMsg);
    return () => window.removeEventListener("message", onMsg);
  }, []);

  // 감정이 크게 변한 축을 잠깐 플래시.
  useEffect(() => {
    const cur = state?.emotion;
    if (!cur) return;
    const prev = prevEmoRef.current;
    prevEmoRef.current = cur;
    if (!prev) return;
    let best: Axis | null = null;
    let bestD = 3;
    (AXES as readonly Axis[]).forEach((a) => {
      const d = Math.abs((cur[a] ?? 0) - (prev[a] ?? 0));
      if (d > bestD) { bestD = d; best = a; }
    });
    if (!best) return;
    setFlashAxis(best);
    const t = setTimeout(() => setFlashAxis(null), 1200);
    return () => clearTimeout(t);
  }, [state?.emotion]);

  useEffect(() => {
    const cur = state?.tier?.name;
    if (!cur) return;
    const prev = prevTierNameRef.current;
    prevTierNameRef.current = cur;
    if (prev && prev !== cur) {
      setTierToast(`${cur} 도달!`);
      if (tierToastTimer.current) clearTimeout(tierToastTimer.current);
      tierToastTimer.current = setTimeout(() => setTierToast(null), 2600);
    }
  }, [state?.tier?.name]);

  useEffect(() => {
    if (state?.is_over && state.game_id && !report) {
      api.getReport(state.game_id).then((r) => { if (r) setReport(r); });
    }
  }, [state?.is_over, state?.game_id, report]);

  // 진단 문항 키보드 입력(1~6 선택, Enter 다음).
  useEffect(() => {
    if (state || step !== 1) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (["1", "2", "3", "4", "5", "6"].includes(e.key)) {
        if (selectQuestionOption(Number(e.key) - 1)) e.preventDefault();
        return;
      }
      if (e.key === "Enter") {
        if (advanceQuestion()) e.preventDefault();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [advanceQuestion, selectQuestionOption, state, step]);

  // 7문항 완답 시 진단 결과 조회.
  useEffect(() => {
    if (state || step < 1) return;
    if (!QUESTIONS.every((q) => q.key in answers)) {
      setDiagnosis(null);
      return;
    }
    let cancelled = false;
    api.diagnoseDisposition(answers).then((d) => {
      if (!cancelled) setDiagnosis(d);
    });
    return () => { cancelled = true; };
  }, [answers, state, step]);

  const start = async () => {
    setBusy(true); setError(null);
    const usedSeed = seed ?? Math.floor(Math.random() * 100000);
    const s = await api.startEmo(answers, usedSeed, 10, levelWeights(levels), name.trim());
    if (s) {
      pendingStartRef.current = s;
      setStoryScene("bridge");
    } else setError("게임을 시작하지 못했어요. 잠시 후 다시 시도해 주세요.");
    setBusy(false);
  };
  const bridgeDone = () => {
    setStoryScene(null);
    const s = pendingStartRef.current;
    pendingStartRef.current = null;
    if (s) setRun(s);
  };

  const resolveChain = async (id: string) => {
    const s = stateRef.current; if (!s) return;
    const cLabel = chain?.choices.find((c) => c.id === id)?.label ?? "";
    if (cLabel) dayLogRef.current.push({ label: cLabel, tag: "hold" });
    setBusy(true); setError(null);
    const ns = await api.chooseChain(s.game_id, id);
    setChain(null);
    if (ns) setRun(ns);
    else setError("요청이 처리되지 않았어요. 다시 시도해 주세요.");
    mapRef.current?.signal({ type: "meeting_done" });
    setBusy(false);
  };

  const showTradeFlash = (action: "buy" | "sell", detail?: string) => {
    setTradeFlash({ action, detail });
    if (tradeFlashTimer.current) clearTimeout(tradeFlashTimer.current);
    tradeFlashTimer.current = setTimeout(() => setTradeFlash(null), 1800);
  };

  const advanceBoard = () => setBoardStep((s) => s + 1);
  const reactBoard = (id: string) => {
    const action = board?.scenario.choices.find((c) => c.id === id)?.action;
    if (action === "buy" || action === "sell") {
      setCoinPick({ action, choiceId: id });
      return;
    }
    boardPickRef.current?.({ id, coin_target: null });
  };
  const pickCoin = (cat: string) => {
    if (!coinPick) return;
    showTradeFlash(coinPick.action === "buy" ? "buy" : "sell");
    boardPickRef.current?.({ id: coinPick.choiceId, coin_target: cat });
    setCoinPick(null);
  };
  const resolveDilemma = (id: string) => {
    if (id === "cash_out" || id === "take_profit" || id === "spend") {
      showTradeFlash("sell", dilemma?.choices.find((c) => c.id === id)?.label);
    }
    dilemmaPickRef.current?.(id);
  };

  const advanceDay = () => {
    const ns = pendingNextRef.current;
    pendingNextRef.current = null;
    setDayReport(null);
    if (ns) setRun(ns);
  };

  const confirmPlan = async (assignment: Record<string, string>) => {
    const s = stateRef.current; if (!s) return;
    setPlanBusy(true); setError(null);
    const ns = await api.submitPlan(s.game_id, assignment);
    setPlanBusy(false);
    if (ns) setRun(ns);
    else setError("일과 편성에 실패했어요. 자동 편성으로 진행할게요.");
    planGateRef.current?.();
  };
  const skipPlan = () => { planGateRef.current?.(); };

  const toDiagnosis = () => setStoryScene("prologue");
  const prologueDone = () => { setStoryScene(null); setStep(1); };
  const toAllocation = () => {
    const s = Math.floor(Math.random() * 100000);
    setSeed(s);
    // T-65 (5안) — 진단 성향으로 배분 프리셋 미리 담기(유저가 아직 안 건드렸을 때만).
    const dt = diagnosis?.declared_type;
    if (dt && allocSource !== "user" && ALLOCATION_PRESET[dt]) {
      setLevels({ ...ALLOCATION_PRESET[dt] });
    }
    setStep(3);
    api.getCatalog(s).then((c) => { if (c) setCatalog(c.coins); });
  };
  const goBack = () => {
    if (step === 1 && questionIndex > 0) { setQuestionIndex((i) => i - 1); return; }
    setStep((s) => Math.max(0, s - 1));
  };
  const goNext = () => {
    if (step === 0) { toDiagnosis(); return; }
    if (step === 1) { advanceQuestion(); return; }
    if (step === 2) { toAllocation(); return; }
    setStep((s) => s + 1);
  };
  const restart = () => {
    setState(null); setAnswers({}); setQuestionIndex(0); setShareCopied(false);
    setReport(null); setStep(0); setEndingCutDone(false); setStoryScene(null);
    setSeed(null); setCatalog(null); setDiagnosis(null); prevTierNameRef.current = null;
    // T-65 — 2회차 회귀 방지: 배분·프리셋 상태 리셋(새 진단이 새 프리셋을 담게).
    setLevels({ ...DEFAULT_LEVELS }); setAllocSource("preset");
    setScreen("title");
  };

  if (screen === "title" || !state) {
    const clone = name.trim() || "클론";
    // 공유 컷씬 배경 하나 위에 타이틀/온보딩/스토리 씬을 얹는다(전환 시 재부팅 없음).
    const content = screen === "title" ? (
      <TitleScreen onNewGame={() => setScreen("game")} />
    ) : storyScene === "prologue" ? (
      <StoryScene cuts={PROLOGUE_CUTS} cloneName={clone} backdrop={false} onDone={prologueDone} />
    ) : storyScene === "bridge" ? (
      <StoryScene cuts={BRIDGE_CUTS(clone)} dim={false} cloneName={clone} backdrop={false} onDone={bridgeDone} />
    ) : (
      <OnboardingWizard
        step={step} name={name} questionIndex={questionIndex} answers={answers}
        diagnosis={diagnosis} levels={levels} catalog={catalog} busy={busy} error={error}
        allocPresetType={allocSource === "preset" ? diagnosis?.declared_type : null}
        onNameChange={setName} onNameSubmit={toDiagnosis}
        onSelectOption={selectQuestionOption}
        onLevelChange={(c, lv: Level) => { setLevels((m) => ({ ...m, [c]: lv })); setAllocSource("user"); }}
        onBack={goBack} onNext={goNext} onStart={start}
        onCopyShare={() => setShareCopied(true)}
        onResetDiagnosis={() => {
          setAnswers({}); setDiagnosis(null); setQuestionIndex(0); setShareCopied(false); setStep(1);
          setAllocSource("preset");   // T-65 — 재진단 시 새 성향 프리셋을 다시 담게
        }}
      />
    );
    return (
      <>
        <CutsceneBackdrop name={storyScene === "prologue" || step > 0 ? name.trim() : ""} />
        {content}
      </>
    );
  }

  if (state.is_over && state.ending) {
    if (!endingCutDone) {
      return <StoryScene cuts={ENDING_PRE_CUT} dim={false} cloneName={state.clone_name} onDone={() => setEndingCutDone(true)} />;
    }
    return <EndingScreen state={state} report={report} onRestart={restart} />;
  }

  // 여론을 다 본 뒤에도 좌측 피드는 유지 — 선택 완료(setBoard(null))에만 닫힌다.
  const boardFeedVisible = !!board && !chain && !dilemma;
  const advEvent = dilemma
    ? {
      speakerId: undefined as string | undefined, speakerName: state.clone_name,
      title: dilemma.title, text: dilemma.text, choices: dilemma.choices,
      run: resolveDilemma, tone: "dilemma" as const
    }
    : chain
      ? {
        speakerId: chain.npc_id as string | undefined, speakerName: undefined as string | undefined,
        title: chain.title, text: chain.text, choices: chain.choices,
        run: resolveChain, tone: "chain" as const
      }
      : board && boardStep >= board.threads.length
        ? {
          speakerId: undefined as string | undefined, speakerName: "게시판",
          title: `게시판 · 여론 ${board.verdict}`, text: board.scenario.text,
          choices: board.scenario.choices, run: reactBoard, tone: "board" as const
        }
        : null;

  return (
    <main className="relative h-screen w-screen overflow-hidden bg-pixel-path flex flex-col gap-2 p-2 sm:p-3">
      <PlayHeader state={state} flashAxis={flashAxis} onOpenPortfolio={() => setShowPortfolio(true)} />

      {state.ticker && state.ticker.length > 0 && (
        <div className="shrink-0 px-1 relative">
          <TickerBar ticker={state.ticker} preOpen={state.day === 0} />
          <CoachMark
            id="tickerBar"
            text="실제 코인의 과거 어느 열흘이에요. 언제인지는 비밀 — 끝나면 공개."
            className="absolute left-0 top-full mt-1"
          />
        </div>
      )}

      {tierToast && (
        <div className="shrink-0 flex justify-center">
          <span className="text-[12px] font-extrabold bg-amber-500 text-black rounded-full px-4 py-1 shadow-pixel-sm border-2 border-black animate-fade-in">
            {tierToast}
          </span>
        </div>
      )}

      <div className="relative flex-1 min-h-0 min-w-0 rounded-xl overflow-hidden border-2 border-black/25">
        <MapBackground ref={mapRef} gameId={state.game_id} game="emo" contained onActivity={() => undefined} />

        {/* 게시판·대화씬 동안 맵 위 은은한 드랍(UI 레이어들 아래) */}
        {(boardFeedVisible || advEvent) && (
          <div className="absolute inset-0 z-[5] bg-black/35 pointer-events-none transition-opacity duration-300" />
        )}

        {tradeFlash && <TradeFlashBadge action={tradeFlash.action} detail={tradeFlash.detail} />}

        {boardFeedVisible && (
          <BoardOpinionFeed board={board!} boardStep={boardStep} onAdvance={advanceBoard} />
        )}

        {advEvent && !coinPick && (
          <div className="absolute right-2 sm:right-3 bottom-40 sm:bottom-44 z-20 flex flex-col items-end gap-2">
            <AdvChoiceMenu choices={advEvent.choices} onChoose={advEvent.run} busy={busy} tone={advEvent.tone} />
            {advEvent.tone === "board" && (
              <CoachMark
                id="firstBoard"
                text="정답은 없어요. 선택은 감정과 내일의 노출을 바꿔요 — 밤에 결과로 보여드려요."
              />
            )}
          </div>
        )}

        {advEvent && coinPick && (
          <CoinPicker
            action={coinPick.action}
            holdings={state.holdings}
            busy={busy}
            onPick={pickCoin}
            onCancel={() => setCoinPick(null)}
          />
        )}

        {advEvent && (
          <div className="absolute inset-x-0 bottom-0 z-10 p-2 sm:p-3">
            <AdvDialogue
              speakerId={advEvent.speakerId}
              speakerName={advEvent.speakerName}
              title={advEvent.title}
              text={advEvent.text}
              tone={advEvent.tone}
            />
          </div>
        )}

        {!advEvent && !boardFeedVisible && (
          <div className="absolute inset-x-0 bottom-2 z-10 flex flex-col items-center gap-2">
            <CoachMark id="walking" text="클론이 당신의 성향대로 하루를 보내는 중이에요." />
          </div>
        )}
      </div>

      {error && (
        <div className="shrink-0 text-[12px] font-bold text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2" role="alert">{error}</div>
      )}

      {showPortfolio && <PortfolioPopover state={state} onClose={() => setShowPortfolio(false)} />}

      {dayReport && <DayReport data={dayReport} onNext={advanceDay} />}

      {planView && (
        <DailyPlan
          plan={planView}
          cloneName={state.clone_name}
          onConfirm={confirmPlan}
          onSkip={skipPlan}
          busy={planBusy}
        />
      )}

      {storyScene === "firstBoard" && (
        <StoryScene overlay cuts={FIRST_BOARD_CUT} onDone={() => storySceneGateRef.current?.()} />
      )}
      {storyScene === "halfway" && (
        <StoryScene overlay cuts={HALFWAY_CUTS(state.clone_name)} onDone={() => storySceneGateRef.current?.()} />
      )}
    </main>
  );
}
