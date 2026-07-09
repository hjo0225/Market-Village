"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { Users, CalendarDays, Wallet, PieChart, X, TrendingUp, TrendingDown } from "lucide-react";
import * as api from "@/lib/emoApi";
import { Board, ChainEvent, Dilemma, EmoState, NPC_NAME, CATEGORIES, CATEGORY_LABEL, Category, AXES, Axis, Emotion } from "@/lib/emoApi";
import EmotionGauge from "@/components/EmotionGauge";
import EmotionStrip from "@/components/EmotionStrip";
import PortfolioPanel from "@/components/PortfolioPanel";
import AdvDialogue from "@/components/AdvDialogue";
import AdvChoiceMenu from "@/components/AdvChoiceMenu";
import DayReport, { DayReportData } from "@/components/DayReport";
import DiagnosisReport from "@/components/DiagnosisReport";
import MapBackground, { MapBackgroundHandle } from "@/components/MapBackground";
import PixelPanel from "@/components/pixel/PixelPanel";
import PixelButton from "@/components/pixel/PixelButton";
import StoryScene, { StoryCut } from "@/components/StoryScene";
import DailyPlan from "@/components/DailyPlan";
import { PlanView } from "@/lib/emoApi";

// §3.1/§3.2/§3.3 — 정적 스토리 씬 스크립트(원문 그대로, LLM 호출 없음·I5).
const PROLOGUE_CUTS: StoryCut[] = [
  { bg: "dark", lines: ["어떤 판단은, 내가 한 게 아니라 내 기분이 한 것이었다."] },
  { lines: ["마켓 빌리지. 주민 전원이 코인을 하는 작은 마을.", "이곳에 당신을 닮은 클론이 이사를 온다."] },
  { lines: ["클론은 당신의 습관대로 기뻐하고, 당신의 습관대로 흔들린다.", "그러니 먼저 — 당신이 어떤 사람인지 알려주세요."] },
];
const BRIDGE_CUTS = (cloneName: string): StoryCut[] => [
  { lines: [`……여기가 마켓 빌리지구나. 이삿짐이라곤 지갑 하나.`], speaker: cloneName },
  { lines: ["마을 사람들은 전부 코인을 한다. 단톡방은 하루 종일 울린다.", "카페의 동수, 광장의 재훈, 펍 구석의 만식…… 곧 다 알게 된다."] },
  { lines: ["당신이 해줄 일은 하나. 클론의 하루를 짜주는 것.", "어디서 시간을 보내는지가, 마음을 만든다. 마음이, 지갑을 지킨다."] },
  { lines: ["그럼 — 첫째 날."] },
];
const ENDING_PRE_CUT: StoryCut[] = [
  { lines: ["열흘 남짓, 클론의 계절이 끝났다. 이제 거울을 볼 시간."] },
];

// T-30 · 초기 배분 UX — 슬라이더 대신 높음/중간/낮음(가중치). 백엔드가 합으로
// 정규화하므로 상대 가중치만 보내면 된다(low1·med2·high3).
type Level = "low" | "med" | "high";
const LEVELS: Level[] = ["low", "med", "high"];
const LEVEL_WEIGHT: Record<Level, number> = { low: 1, med: 2, high: 3 };
const LEVEL_LABEL: Record<Level, string> = { low: "낮음", med: "중간", high: "높음" };
const DEFAULT_LEVELS: Record<Category, Level> = {
  large_stable: "med", mid_alt: "med", meme: "low", stable: "low", cash: "med",
};

// T-47e — 정적 성향 진단 7문항(spec docs/STATIC_DISPOSITION_SPEC.md §1). 값=점수
// (1~4, 높을수록 위험지향). 백엔드 disposition.diagnose가 점수로 선택지를 역참조.
const QUESTIONS: { key: string; text: string; options: [string, number][] }[] = [
  { key: "Q1", text: "룸메이트가 눈을 반짝이며 말한다. \"지금 아니면 못 사. 다들 타는 중이야.\" 너라면?",
    options: [["바로 산다. 기회는 안 기다려준다", 4], ["일단 뭔지 좀 알아본다", 2], ["다들 탈 때가 제일 위험하다. 무시", 1]] },
  { key: "Q2", text: "투자한 돈이 하루 만에 −30%. 지금 네 심정은?",
    options: [["기회다. 오히려 더 산다", 4], ["오를 때까지 버틴다(존버)", 3], ["정해둔 선에서 손절한다", 2], ["밤새 잠을 못 잔다", 1]] },
  { key: "Q3", text: "예상 못 한 100만원이 생겼다. 어디에 넣어?",
    options: [["신규/알트코인에 전부", 4], ["비트·이더 같은 메이저에", 3], ["절반만 투자, 절반은 예금", 2], ["전액 예적금", 1]] },
  { key: "Q4", text: "너에게 '투자'란 한마디로?",
    options: [["인생 역전의 기회", 4], ["자산을 불리는 수단", 3], ["노후를 위한 준비", 2], ["안 잃는 게 최우선", 1]] },
  { key: "Q5", text: "얼마까지 잃어도 네 일상이 흔들리지 않아?",
    options: [["전액 각오돼 있다", 4], ["절반 정도까지", 3], ["10% 정도까지", 2], ["한 푼도 잃기 싫다", 1]] },
  { key: "Q6", text: "수익이 났다. 넌 언제 팔아?",
    options: [["목표가까지 안 판다", 4], ["조금 오르면 바로 익절", 2], ["원금 회복하는 순간 판다", 1]] },
  { key: "Q7", text: "코인 결정을 내릴 때 넌 주로 뭘 믿어?",
    options: [["커뮤니티/인플루언서 분위기", 4], ["유튜브·뉴스의 분석", 3], ["내가 직접 조사한 자료", 2], ["아무도 안 믿는다, 안 한다", 1]] },
];

export default function EmoPage() {
  const [state, setState] = useState<EmoState | null>(null);
  const [board, setBoard] = useState<Board | null>(null);
  const [boardStep, setBoardStep] = useState(0);   // T-41 — 여론 넘겨보기 인덱스(미연시, 글 단위)
  const [chain, setChain] = useState<ChainEvent | null>(null);
  const [dilemma, setDilemma] = useState<Dilemma | null>(null);   // T-30c 캐시아웃 딜레마
  const dilemmaPickRef = useRef<((id: string) => void) | null>(null);
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [name, setName] = useState("");   // T-28 — 클론 이름
  const [levels, setLevels] = useState<Record<Category, Level>>({ ...DEFAULT_LEVELS });   // T-30
  const [step, setStep] = useState(0);   // T-29 — 온보딩 스텝(0 이름 · 1 진단 · 2 배분)
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mapActivity, setMapActivity] = useState<string | null>(null);
  const [showPortfolio, setShowPortfolio] = useState(false);   // T-31 포트폴리오 드로어
  const [flashAxis, setFlashAxis] = useState<Axis | null>(null);   // T-35 감정 변화 플래시
  const [tradeFlash, setTradeFlash] = useState<"buy" | "sell" | null>(null);   // T-35 매매 배지
  const tradeFlashTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const prevEmoRef = useRef<Emotion | null>(null);
  const [dayReport, setDayReport] = useState<DayReportData | null>(null);   // T-33/T-34 취침+정산
  const [report, setReport] = useState<api.DiagnosisReport | null>(null);   // T-47e 진단 리포트(엔딩 후)
  const pendingNextRef = useRef<EmoState | null>(null);
  const mapRef = useRef<MapBackgroundHandle>(null);
  const stateRef = useRef<EmoState | null>(null);
  const boardPickRef = useRef<((id: string) => void) | null>(null);
  const day = state?.day ?? -1;

  // §3 — 스토리 씬 게이트. "prologue"=이름→진단 사이, "bridge"=배분 완료→Day0 시작
  // 사이, "endingPre"=엔딩 텍스트 앞 1컷. null이면 씬 없음(평시).
  const [storyScene, setStoryScene] = useState<"prologue" | "bridge" | "endingPre" | null>(null);
  const [endingCutDone, setEndingCutDone] = useState(false);   // §3.3 — 엔딩 1컷은 1회만
  const pendingStartRef = useRef<EmoState | null>(null);   // bridge 씬 종료 후 진입할 state

  // §2.3 — 「오늘의 일과」 편성 화면. GET /plan이 404(백엔드 미배포)거나 이미
  // locked면 조용히 자동 편성(기존 루트, I6)으로 폴백.
  const [planView, setPlanView] = useState<PlanView | null>(null);
  const planGateRef = useRef<(() => void) | null>(null);
  const [planBusy, setPlanBusy] = useState(false);

  const setRun = useCallback((s: EmoState) => { stateRef.current = s; setState(s); }, []);

  // T-22/A — 하루 일과: 클론이 시간대별로 걷고, 그 도중 만남·게시판이 등장한다.
  // 게시판(그날 시장 이벤트)은 랜덤 밴드에 도착 → 반응 선택은 그 자리에서 받되,
  // 정산(choose: 감정·시장·리밸런싱 + day++)은 남은 하루를 다 걷고 **저녁에** 한다.
  // (사용자: "선택 후 남은 하루를 걷고" — 선택=하루 끝이 아니라 하루 중 반응.)
  useEffect(() => {
    if (day < 0) return;
    let s = stateRef.current;
    if (!s || s.is_over) { setBoard(null); setChain(null); return; }
    let cancelled = false;
    (async () => {
      setBoard(null); setChain(null); setDilemma(null);
      // §2.3 — 하루 시작 시 「오늘의 일과」 편성 게이트. GET /plan이 성공하고
      // 잠기지 않았으면 편성 화면을 띄우고 확정(POST)/자동편성(스킵)을 기다린다.
      // 404 등으로 null이면 조용히 건너뛰어 기존 자동 루트로(I6).
      const pv = await api.getPlan(s.game_id);
      if (cancelled) return;
      if (pv && !pv.locked) {
        setPlanView(pv);
        await new Promise<void>((resolve) => { planGateRef.current = resolve; });
        planGateRef.current = null;
        setPlanView(null);
        // confirmPlan이 POST 성공 시 stateRef를 새 band_places로 갱신했을 수 있어
        // 재확보(장소 딜레마 판단이 최신 편성을 봐야 함).
        s = stateRef.current ?? s;
      }
      if (cancelled) return;
      // T-30c — 하루 시작에 캐시아웃 딜레마(발동 조건 충족 시 1회). 날짜는 안 넘어감.
      if (s.has_cashout_dilemma) {
        const dil = await api.getDilemma(s.game_id);
        if (dil && !cancelled) {
          setDilemma(dil);
          const cid = await new Promise<string>((resolve) => { dilemmaPickRef.current = resolve; });
          dilemmaPickRef.current = null;
          setDilemma(null);
          if (!cancelled) {
            const ns = await api.chooseDilemma(s.game_id, cid);
            if (ns && !cancelled) setRun(ns);   // day 불변 → 일과 시퀀스 재실행 안 됨
          }
        }
      }
      if (cancelled) return;
      const bands = ["오전", "점심", "오후", "저녁"];
      // 게시판이 터지는 밴드 = **점심 고정**. 오전 제외(아침은 걷게 두고 그 뒤에)·
      // 저녁 제외(반응 후 걸을 하루가 남게)·**오후 제외(동행 만남이 오후라 겹침)**.
      // 점심에 반응을 끝내면 for-loop이 그때 대기하므로 오후 만남과 순차 진행된다
      // (게시판·만남 동시 표시 충돌 방지, 사용자 2026-07-08).
      const boardBand = "점심";
      let picked: string | null = null;
      let pickedLabel = "";
      for (const band of bands) {
        if (cancelled) return;
        await mapRef.current?.playWalk(band, 2);   // 만남은 리스너가 도중 처리
        if (cancelled) return;
        if (band === boardBand) {
          // 그날 시장 이벤트 도착 — 걷기 정지, 반응만 받고(정산은 저녁) 게시판 닫음.
          const b = await api.getBoard(s.game_id);
          if (cancelled || !b) continue;
          setBoardStep(0);   // T-41 — 여론 첫 글부터 넘겨보기
          setBoard(b);
          picked = await new Promise<string>((resolve) => { boardPickRef.current = resolve; });
          boardPickRef.current = null;
          pickedLabel = b.scenario.choices.find((c) => c.id === picked)?.label ?? "";
          if (cancelled) return;
          setBoard(null);   // 반응 후 닫고 남은 하루를 마저 걷는다
        }
        // T-50d — 장소 딜레마: 그 장소(도서관 익절복기·마켓 현실소비=disp 결정점)에
        // 도착하면 발동. 오전·저녁만(점심=게시판·오후=동행과 겹침 방지). day 불변이라
        // 일과 시퀀스 재실행 없음(멱등: 리로드 시 place_dilemmas_done가 이중적용 차단).
        const bandPlace = s.band_places?.[band];
        if ((band === "오전" || band === "저녁") && (bandPlace === "도서관" || bandPlace === "마켓")) {
          const pdil = await api.getPlaceDilemma(s.game_id, bandPlace);
          if (pdil && !cancelled) {
            setDilemma({ ...pdil, gain: false });
            const cid = await new Promise<string>((resolve) => { dilemmaPickRef.current = resolve; });
            dilemmaPickRef.current = null;
            setDilemma(null);
            if (!cancelled) {
              const ns = await api.choosePlaceDilemma(s.game_id, bandPlace, cid);
              if (ns && !cancelled) setRun(ns);
            }
          }
        }
      }
      if (cancelled) return;
      // 저녁 정산 — 낮에 고른 반응을 반영(감정·시장·리밸런싱) + 다음 날.
      if (picked) {
        const ns = await api.choose(s.game_id, picked);
        if (cancelled) return;
        if (!ns) { setError("정산에 실패했어요. 다시 시도해 주세요."); return; }
        if (ns.is_over) { setRun(ns); return; }   // 마지막 날 → 엔딩으로
        // T-33/T-34 — 취침 암전 + 하루 정산 리포트. "다음 날" 누르면 진행.
        // prev = 정산 직전 상태(딜레마가 갱신했을 수 있어 stateRef에서 읽는다).
        const prev = stateRef.current ?? s;
        pendingNextRef.current = ns;
        setDayReport({
          day: prev.day, name: prev.clone_name,
          prevEmotion: prev.emotion, nextEmotion: ns.emotion,
          prevAsset: prev.portfolio_value, nextAsset: ns.portfolio_value,
          prevHoldings: prev.holdings, nextHoldings: ns.holdings,   // T-38 — 카테고리별 변화
          choiceLabel: pickedLabel,
          market: ns.last_market,
          settlement: ns.settlement,   // §5.1 — 있으면 DayReport가 cascade 단계 추가(I6: 없으면 폴백)
        });
      }
    })();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [day]);

  // T-22/A — 맵에서 클론이 companion에 도착하면(meeting_talk) 만남 카드를 연다.
  useEffect(() => {
    const onMsg = async (e: MessageEvent) => {
      if (e.data?.type !== "meeting_talk") return;
      mapRef.current?.signal({ type: "meeting_ack" });
      const s = stateRef.current;
      if (s && s.has_pending_chain) {
        const ch = await api.getChain(s.game_id);
        if (ch) { setChain(ch); return; }   // 카드 표시 → 응답이 meeting_done을 보냄
      }
      mapRef.current?.signal({ type: "meeting_done" });   // 체인 없으면 지나감
    };
    window.addEventListener("message", onMsg);
    return () => window.removeEventListener("message", onMsg);
  }, []);

  // T-35 — 감정 변화 체감: 값이 바뀌면 가장 크게 변한 축을 잠깐 플래시.
  useEffect(() => {
    const cur = state?.emotion;
    if (!cur) return;
    const prev = prevEmoRef.current;
    prevEmoRef.current = cur;
    if (!prev) return;
    let best: Axis | null = null;
    let bestD = 3;   // 임계 — 미세 변화는 무시
    (AXES as readonly Axis[]).forEach((a) => {
      const d = Math.abs((cur[a] ?? 0) - (prev[a] ?? 0));
      if (d > bestD) { bestD = d; best = a; }
    });
    if (!best) return;
    setFlashAxis(best);
    const t = setTimeout(() => setFlashAxis(null), 1200);
    return () => clearTimeout(t);
  }, [state?.emotion]);

  // T-47e — 엔딩 도달 시 진단 리포트(선언 vs 실제 편향)를 1회 가져온다(멱등 GET).
  useEffect(() => {
    if (state?.is_over && state.game_id && !report) {
      api.getReport(state.game_id).then((r) => { if (r) setReport(r); });
    }
  }, [state?.is_over, state?.game_id, report]);

  // §3.2 — 자산 배분 완료(POST /start 성공) → 브릿지 씬 → Day 0 시작. 씬 종료
  // (건너뛰기 포함) 시 pendingStartRef의 state로 진입(bridgeDone이 처리).
  const start = async () => {
    setBusy(true); setError(null);
    const seed = Math.floor(Math.random() * 100000);
    // T-30 — 높음/중간/낮음 → 상대 가중치(백엔드가 합으로 정규화).
    const weights: Record<string, number> = {};
    CATEGORIES.forEach((c) => { weights[c] = LEVEL_WEIGHT[levels[c]]; });
    const s = await api.startEmo(answers, seed, 20, weights, name.trim());   // T-48f — 20일(표본 견고화)
    if (s) { pendingStartRef.current = s; setStoryScene("bridge"); }
    else setError("게임을 시작하지 못했어요. 잠시 후 다시 시도해 주세요.");
    setBusy(false);
  };
  const bridgeDone = () => {
    setStoryScene(null);
    const s = pendingStartRef.current;
    pendingStartRef.current = null;
    if (s) setRun(s);
  };

  // 만남(체인) 응답 — 걷기 도중. day 불변이라 일과 시퀀스 재실행 안 함.
  const resolveChain = async (id: string) => {
    const s = stateRef.current; if (!s) return;
    setBusy(true); setError(null);
    const ns = await api.chooseChain(s.game_id, id);
    setChain(null);
    if (ns) setRun(ns);
    else setError("요청이 처리되지 않았어요. 다시 시도해 주세요.");
    mapRef.current?.signal({ type: "meeting_done" });   // 걷기 계속
    setBusy(false);
  };

  // T-35 — 매매 순간 체감: 결정적 매매를 골랐을 때 맵 위에 매매 배지를 잠깐 띄운다.
  // (맵 말풍선 trade_fx는 직후 재개되는 걷기 🚶에 즉시 덮여 안 보임 → React 레이어로.)
  const showTradeFlash = (action: "buy" | "sell") => {
    setTradeFlash(action);
    if (tradeFlashTimer.current) clearTimeout(tradeFlashTimer.current);
    tradeFlashTimer.current = setTimeout(() => setTradeFlash(null), 1400);
  };

  // 게시판 반응 — 낮에 고름. 정산은 아니고(저녁에 함) 일과 시퀀스의 대기를 푼다.
  // 고른 반응의 position으로 매매 배지를 띄운다. 관망(-0.2)·소액 태움(0.1) 같은
  // **소극적 선택**엔 안 뜨게 결정적 매매(|position|≥0.25)만.
  const TRADE_FX_MIN = 0.25;
  // T-41 — 게시판 여론 미연시 넘기기: 글(post)을 한 명씩 보고 클릭으로 다음 글 →
  // 마지막 글 다음에 이벤트 요약+선택지가 뜬다(아래 advEvent board 분기).
  const advanceBoard = () => setBoardStep((s) => s + 1);
  const reactBoard = (id: string) => {
    const pos = board?.scenario.choices.find((c) => c.id === id)?.position ?? 0;
    if (pos >= TRADE_FX_MIN) showTradeFlash("buy");
    else if (pos <= -TRADE_FX_MIN) showTradeFlash("sell");
    boardPickRef.current?.(id);
  };
  // T-30c — 캐시아웃 딜레마 응답. 현금화(cash_out)=위험자산 매도 → 매매 배지.
  const resolveDilemma = (id: string) => {
    // 현금화·익절·소비 = 이익 실현(매도) → 매도 배지. (T-50d: take_profit·spend)
    if (id === "cash_out" || id === "take_profit" || id === "spend") showTradeFlash("sell");
    dilemmaPickRef.current?.(id);
  };

  // T-33/T-34 — 정산 리포트에서 "다음 날" → 다음 날로 진행(일과 시퀀스 재시작).
  const advanceDay = () => {
    const ns = pendingNextRef.current;
    pendingNextRef.current = null;
    setDayReport(null);
    if (ns) setRun(ns);
  };

  // §2.3 — 「오늘의 일과」 확정: POST /plan → 성공하면 상태 갱신 후 걷기 시퀀스로
  // 진입(게이트 해제). 실패해도 게이트는 풀어 자동 루트로 이어간다(I6 폴백).
  const confirmPlan = async (assignment: Record<string, string>) => {
    const s = stateRef.current; if (!s) return;
    setPlanBusy(true); setError(null);
    const ns = await api.submitPlan(s.game_id, assignment);
    setPlanBusy(false);
    if (ns) setRun(ns);
    else setError("일과 편성에 실패했어요. 자동 편성으로 진행할게요.");
    planGateRef.current?.();
  };
  // "자동 편성" 스킵 — 플랜 미제출, 기존 자동 루트 유지(I6).
  const skipPlan = () => { planGateRef.current?.(); };

  // §3.1 — 이름 입력(step 0) → 설문(step 1) 사이 프롤로그. 이름을 확정하면 씬을
  // 먼저 보여주고, 씬이 끝나면(건너뛰기 포함) step 1로 진입.
  const toDiagnosis = () => setStoryScene("prologue");
  const prologueDone = () => { setStoryScene(null); setStep(1); };

  // ---------- 온보딩 위저드(T-29: 한 화면 한 목적 — 이름 → 진단 → 배분) ----------
  if (!state) {
    if (storyScene === "prologue") return <StoryScene cuts={PROLOGUE_CUTS} onDone={prologueDone} />;
    if (storyScene === "bridge") return <StoryScene cuts={BRIDGE_CUTS(name.trim() || "클론")} onDone={bridgeDone} />;
    const diagnosisReady = QUESTIONS.every((q) => q.key in answers);
    const totalW = CATEGORIES.reduce((s, c) => s + LEVEL_WEIGHT[levels[c]], 0);
    const STEP_TITLE = ["이사 온 날", "투자 성향 진단", "초기 자산 배분"];
    return (
      <main className="min-h-screen bg-pixel-path flex items-center justify-center p-4">
        <PixelPanel tone="wall" className="w-full max-w-lg p-6">
          {/* 진행 표시 */}
          <div className="flex items-center gap-1.5 mb-4">
            {[0, 1, 2].map((i) => (
              <div key={i} className={`h-1.5 flex-1 rounded-full ${i <= step ? "bg-black/70" : "bg-black/15"}`} />
            ))}
          </div>
          <div className="text-[11px] text-pixel-muted mb-1">{step + 1} / 3</div>
          <h1 className="text-lg font-extrabold mb-5">{STEP_TITLE[step]}</h1>

          {/* STEP 0 — 이름만 */}
          {step === 0 && (
            <div>
              <p className="text-[12px] text-pixel-muted mb-4">이 마을에서 30일을 살아갈 내 클론의 이름을 지어주세요.</p>
              <label htmlFor="clone-name" className="text-[13px] font-bold block mb-2">클론 이름</label>
              <input
                id="clone-name" type="text" value={name} maxLength={12}
                placeholder="내 클론"
                autoFocus
                className="w-full px-3 py-2.5 text-[14px] rounded-lg border-2 border-black/15 bg-white focus:border-black/40 outline-none"
                onChange={(e) => setName(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") toDiagnosis(); }}
              />
            </div>
          )}

          {/* STEP 1 — 진단 */}
          {step === 1 && (
            <div className="flex flex-col gap-4">
              <p className="text-[12px] text-pixel-muted -mt-2 mb-1">몇 가지로 당신의 투자 성향을 진단해요.</p>
              {QUESTIONS.map((q) => (
                <div key={q.key}>
                  <div className="text-[13px] font-bold mb-2">{q.text}</div>
                  <div className="flex flex-wrap gap-2">
                    {q.options.map(([label, val]) => (
                      <PixelButton
                        key={label} size="sm"
                        variant={answers[q.key] === val ? "primary" : "ghost"}
                        onClick={() => setAnswers((a) => ({ ...a, [q.key]: val }))}
                      >
                        {label}
                      </PixelButton>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* STEP 2 — 배분 */}
          {step === 2 && (
            <div>
              <p className="text-[12px] text-pixel-muted -mt-2 mb-3">각 자산에 얼마나 담을지 고르세요. 현금(KRW)은 시장 밖 마른 장작이에요.</p>
              <div className="flex flex-col gap-2.5">
                {CATEGORIES.map((c: Category) => {
                  const pct = totalW > 0 ? Math.round((LEVEL_WEIGHT[levels[c]] / totalW) * 100) : 0;
                  return (
                    <div key={c} className="flex items-center gap-3 text-[12px]">
                      <span className="w-24 shrink-0 text-pixel-muted">{CATEGORY_LABEL[c]}</span>
                      <div className="flex gap-1 flex-1">
                        {LEVELS.map((lv) => (
                          <PixelButton
                            key={lv} size="sm"
                            variant={levels[c] === lv ? "primary" : "ghost"}
                            className="flex-1"
                            onClick={() => setLevels((m) => ({ ...m, [c]: lv }))}
                          >
                            {LEVEL_LABEL[lv]}
                          </PixelButton>
                        ))}
                      </div>
                      <span className="w-9 text-right font-bold tabular-nums">{pct}%</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {error && (
            <p className="mt-4 text-[12px] font-bold text-red-600" role="alert">{error}</p>
          )}

          {/* 네비게이션 */}
          <div className="flex gap-2 mt-6">
            {step > 0 && (
              <PixelButton size="lg" variant="ghost" className="shrink-0" onClick={() => setStep((s) => s - 1)}>
                ← 뒤로
              </PixelButton>
            )}
            {step < 2 ? (
              <PixelButton
                size="lg" className="flex-1"
                disabled={step === 1 && !diagnosisReady}
                onClick={() => (step === 0 ? toDiagnosis() : setStep((s) => s + 1))}
              >
                다음 →
              </PixelButton>
            ) : (
              <PixelButton size="lg" className="flex-1" disabled={busy} onClick={start}>
                {busy ? "시작하는 중…" : "이사 온 날 →"}
              </PixelButton>
            )}
          </div>
        </PixelPanel>
      </main>
    );
  }

  // ---------- 엔딩 ----------
  if (state.is_over && state.ending) {
    // §3.3 — 엔딩 텍스트 앞 짧은 1컷("열흘 남짓…"). 1회만 보여주고 넘어간다.
    if (!endingCutDone) {
      return <StoryScene cuts={ENDING_PRE_CUT} onDone={() => setEndingCutDone(true)} />;
    }
    const e = state.ending;
    return (
      <main className="min-h-screen bg-pixel-path flex items-start justify-center p-4 overflow-y-auto">
        <PixelPanel tone="cloud" className="w-full max-w-lg p-6 my-4">
          <div className="text-[11px] text-pixel-muted mb-1">{e.id} · {e.grade}</div>
          <h1 className="text-xl font-extrabold mb-4">{e.title}</h1>
          <div className="flex flex-col gap-3 text-[13px] leading-relaxed">
            {e.epilogue.map((line, i) => (
              <p key={i} className="border-l-2 border-black/10 pl-3">{line}</p>
            ))}
          </div>
          <div className="mt-5 text-[11px] text-pixel-muted">
            {state.clone_name} · 최종 자산 {Math.round(state.portfolio_value).toLocaleString()} · 특수이벤트 {state.special_event_count}회
          </div>

          {/* T-47e — 진단 리포트(선언 vs 실제 편향) */}
          <DiagnosisReport report={report} />

          <PixelButton size="lg" className="w-full mt-6" onClick={() => { setState(null); setAnswers({}); setReport(null); setStep(0); setEndingCutDone(false); setStoryScene(null); }}>
            다시 시작
          </PixelButton>
        </PixelPanel>
      </main>
    );
  }

  // ---------- 플레이 (하이브리드 ADV: 상단 감정스트립 / 큰 맵 / 하단 JRPG 대사창) ----------
  // T-41 — 게시판 여론 넘겨보기 중(글 3개를 한 명씩)에는 선택지 대신 여론 대사창만 뜬다.
  // 마지막 글 다음(boardStep >= threads.length)에 비로소 이벤트 요약+선택지(advEvent board 분기).
  const boardOnOpinion = !!board && !chain && !dilemma && boardStep < board.threads.length;
  const advEvent = dilemma
    ? { speakerId: undefined as string | undefined, speakerName: state.clone_name,
        title: dilemma.title, text: dilemma.text, choices: dilemma.choices,
        run: resolveDilemma, tone: "dilemma" as const }
    : chain
    ? { speakerId: chain.npc_id as string | undefined, speakerName: undefined as string | undefined,
        title: chain.title, text: chain.text, choices: chain.choices,
        run: resolveChain, tone: "chain" as const }
    : board && boardStep >= board.threads.length
    ? { speakerId: undefined as string | undefined, speakerName: "게시판",
        title: `게시판 · 여론 ${board.verdict}`, text: board.scenario.text,
        choices: board.scenario.choices, run: reactBoard, tone: "board" as const }
    : null;

  return (
    <main className="relative h-screen w-screen overflow-hidden bg-pixel-path flex flex-col gap-2 p-2 sm:p-3">
      {/* 상단 슬림바: 이름·Day·자산·동행 + 감정 스트립(항상 노출) + 포트폴리오 토글 */}
      <header className="shrink-0 flex items-center gap-3 flex-wrap px-1">
        <span className="text-[12px] font-extrabold">{state.clone_name}</span>
        <span className="inline-flex items-center gap-1 text-[11px] font-bold"><CalendarDays className="w-3.5 h-3.5" />Day {state.day + 1}/{state.total_days}</span>
        <span className="inline-flex items-center gap-1 text-[11px] font-bold"><Wallet className="w-3.5 h-3.5" />{Math.round(state.portfolio_value).toLocaleString()}</span>
        {state.companion && (
          <span className="inline-flex items-center gap-1 text-[11px] font-bold"><Users className="w-3.5 h-3.5" />{NPC_NAME[state.companion] ?? state.companion}</span>
        )}
        <span className="hidden sm:block ml-auto"><EmotionStrip emotion={state.emotion} flash={flashAxis} /></span>
        <button
          onClick={() => setShowPortfolio(true)}
          className="ml-auto sm:ml-2 inline-flex items-center gap-1 text-[11px] font-bold bg-black/5 rounded px-2 py-1"
        >
          <PieChart className="w-3.5 h-3.5" />포트폴리오
        </button>
      </header>
      {/* 모바일: 감정 스트립 둘째 줄 */}
      <div className="sm:hidden shrink-0 px-1"><EmotionStrip emotion={state.emotion} flash={flashAxis} /></div>

      {/* 큰 맵/씬 창 — say·choice 스크린이 맵 안에 오버레이(정통 ADV, 분리) */}
      <div className="relative flex-1 min-h-0 min-w-0 rounded-xl overflow-hidden border-2 border-black/25">
        <MapBackground ref={mapRef} gameId={state.game_id} game="emo" contained onActivity={setMapActivity} />

        {/* T-35 — 매매 체감 배지: 결정적 반응 직후 맵 위에 잠깐(1.4s). */}
        {tradeFlash && (
          <div className="absolute inset-x-0 top-[16%] z-30 flex justify-center pointer-events-none">
            <span className={`inline-flex items-center gap-1.5 text-[14px] font-extrabold text-white rounded-full px-4 py-1.5 shadow-lg animate-pulse ${tradeFlash === "buy" ? "bg-rose-600/90" : "bg-sky-600/90"}`}>
              {tradeFlash === "buy" ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
              {tradeFlash === "buy" ? "클론 매수" : "클론 매도"}
            </span>
          </div>
        )}

        {/* T-41 — 게시판 여론 미연시 넘기기: 우상단 동시노출 대신, 글(post)을 하단
            대사창에서 한 명씩 표시하고 클릭(▶)으로 다음 글로 넘긴다. 마지막 글 다음에
            이벤트 요약+선택지(advEvent board 분기)가 뜬다. */}
        {boardOnOpinion && (
          <button
            type="button"
            onClick={advanceBoard}
            aria-label="다음 여론 보기"
            className="absolute inset-x-0 bottom-0 z-10 p-2 sm:p-3 text-left cursor-pointer"
          >
            <AdvDialogue
              speakerId={board!.threads[boardStep].author_id}
              title={`게시판 여론 · ${boardStep + 1}/${board!.threads.length}`}
              text={board!.threads[boardStep].text}
              tone="board"
            />
            <div className="mt-1 pr-1 text-right text-[12px] font-extrabold text-white/85 animate-pulse">▶ 클릭</div>
          </button>
        )}

        {/* choice 스크린 — say와 분리, 맵 중앙에 창형 메뉴 */}
        {advEvent && (
          <div className="absolute inset-x-0 top-[34%] z-20 flex justify-center px-3">
            <AdvChoiceMenu choices={advEvent.choices} onChoose={advEvent.run} busy={busy} tone={advEvent.tone} />
          </div>
        )}

        {/* say 스크린 — 맵 하단 대사 텍스트박스 */}
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

        {/* 걷기 상태(이벤트·여론 없을 때) — 맵 하단 얇은 라벨 */}
        {!advEvent && !boardOnOpinion && (
          <div className="absolute inset-x-0 bottom-2 z-10 flex justify-center">
            <span className="text-[12px] font-bold bg-black/55 text-white rounded px-3 py-1">
              {mapActivity ?? "클론이 하루를 보내는 중…"}
            </span>
          </div>
        )}
      </div>

      {/* 에러(맵 밖 얇은 바) */}
      {error && (
        <div className="shrink-0 text-[12px] font-bold text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2" role="alert">{error}</div>
      )}

      {/* 포트폴리오·감정 드로어(탭) */}
      {showPortfolio && (
        <div className="absolute inset-0 z-20 bg-black/40 flex justify-end" onClick={() => setShowPortfolio(false)}>
          <div className="w-80 max-w-[85%] h-full bg-pixel-path p-3 overflow-y-auto flex flex-col gap-2" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-extrabold">상태</h2>
              <button onClick={() => setShowPortfolio(false)} aria-label="닫기"><X className="w-5 h-5" /></button>
            </div>
            <EmotionGauge emotion={state.emotion} verdict={state.verdict} />
            <PortfolioPanel holdings={state.holdings} />
          </div>
        </div>
      )}

      {/* T-33/T-34 — 취침 암전 + 하루 정산 리포트 */}
      {dayReport && <DayReport data={dayReport} onNext={advanceDay} />}

      {/* §2.3 — 「오늘의 일과」 편성(하루 시작 게이트). 확정 → POST /plan → 기존
          4밴드 걷기 시퀀스 시작. "자동 편성" → 플랜 미제출, 기존 자동 루트(I6). */}
      {planView && (
        <DailyPlan
          plan={planView}
          cloneName={state.clone_name}
          onConfirm={confirmPlan}
          onSkip={skipPlan}
          busy={planBusy}
        />
      )}
    </main>
  );
}
