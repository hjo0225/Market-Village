"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
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
import InvestmentTypeCard from "@/components/InvestmentTypeCard";
import MapBackground, { MapBackgroundHandle } from "@/components/MapBackground";
import PixelPanel from "@/components/pixel/PixelPanel";
import PixelButton from "@/components/pixel/PixelButton";

// T-30 · 초기 배분 UX — 슬라이더 대신 높음/중간/낮음(가중치). 백엔드가 합으로
// 정규화하므로 상대 가중치만 보내면 된다(low1·med2·high3).
type Level = "low" | "med" | "high";
const LEVELS: Level[] = ["low", "med", "high"];
const LEVEL_WEIGHT: Record<Level, number> = { low: 1, med: 2, high: 3 };
const LEVEL_LABEL: Record<Level, string> = { low: "낮음", med: "중간", high: "높음" };
const DEFAULT_LEVELS: Record<Category, Level> = {
  large_stable: "med", mid_alt: "med", meme: "low", stable: "low", cash: "med",
};

// 성향분석.md — 전국투자자교육협의회 '투자 성향 진단표' 7문항을 코인 맥락으로 재구성.
// 값=문항별 가중 점수(문항 내 유일). 백엔드 disposition.diagnose가 점수로 선택지를 역참조.
const QUESTIONS: { key: string; text: string; options: [string, number][] }[] = [
  {
    key: "Q1", text: "여유자금 1,000만 원이 생겼다. 예금과 코인에 나눈다면?",
    options: [["예금 1,000만 원", 2], ["예금 700 · 코인 300", 4], ["예금 500 · 코인 500", 6], ["예금 300 · 코인 700", 8], ["코인 1,000만 원", 10]]
  },
  {
    key: "Q2", text: "이 자금을 얼마 동안 굴릴 생각이야?",
    options: [["1개월 미만", 1], ["1개월 이상 ~ 6개월 미만", 2], ["6개월 이상 ~ 1년 미만", 3], ["1년 이상 ~ 3년 미만", 4], ["3년 이상", 5]]
  },
  {
    key: "Q3", text: "매달 남는 100만 원을 적금과 코인 적립에 나눈다면?",
    options: [["적금 100만 원", 2], ["적금 70 · 코인 30", 4], ["적금 50 · 코인 50", 6], ["적금 30 · 코인 70", 8], ["코인 100만 원", 10]]
  },
  {
    key: "Q4", text: "자산관리에서 내가 우선하는 순서는?",
    options: [["안전성 > 유동성 > 수익성", 1], ["안전성 > 수익성 > 유동성", 2], ["유동성 > 안전성 > 수익성", 3], ["유동성 > 수익성 > 안전성", 4], ["수익성 > 안전성 > 유동성", 5], ["수익성 > 유동성 > 안전성", 6]]
  },
  {
    key: "Q5", text: "가장 선호하는 자산은?",
    options: [["예금 · 스테이블코인", 2], ["비트코인 · 이더 같은 우량 코인", 4], ["신규 · 알트코인", 6]]
  },
  {
    key: "Q6", text: "더 선호하는 투자 전략은?",
    options: [["분산된 포트폴리오로 시장 평균 정도의 성과", 3], ["원금 손실 위험이 있어도 시장 평균보다 높은 수익", 6]]
  },
  {
    key: "Q7", text: "투자 손실을 어디까지 견딜 수 있어?",
    options: [["무슨 일이 있어도 원금은 지켜야 한다", 2], ["10% 미만까지는 감수", 4], ["20% 미만까지는 감수", 6], ["40% 미만까지는 감수", 8], ["기대수익이 높다면 위험은 상관없다", 10]]
  },
];

export default function EmoPage() {
  const [state, setState] = useState<EmoState | null>(null);
  const [board, setBoard] = useState<Board | null>(null);
  const [boardStep, setBoardStep] = useState(0);   // T-41 — 여론 넘겨보기 인덱스(미연시, 글 단위)
  const [chain, setChain] = useState<ChainEvent | null>(null);
  const [dilemma, setDilemma] = useState<Dilemma | null>(null);   // T-30c 캐시아웃 딜레마
  const dilemmaPickRef = useRef<((id: string) => void) | null>(null);
  const [answers, setAnswers] = useState<Record<string, number>>({});
  const [questionIndex, setQuestionIndex] = useState(0);
  const [diagnosis, setDiagnosis] = useState<api.DispositionDiagnosis | null>(null);
  const [shareCopied, setShareCopied] = useState(false);
  const [name, setName] = useState("");   // T-28 — 클론 이름
  const [levels, setLevels] = useState<Record<Category, Level>>({ ...DEFAULT_LEVELS });   // T-30
  const [step, setStep] = useState(0);   // 온보딩 스텝(0 이름 · 1 진단 · 2 결과 · 3 배분)
  const [started, setStarted] = useState(false);   // 인트로 스플래시 → 시작 여부
  const [canStart, setCanStart] = useState(false);   // 몇 초 뒤 "click to start" 노출
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mapActivity, setMapActivity] = useState<string | null>(null);
  const [showPortfolio, setShowPortfolio] = useState(false);   // T-31 포트폴리오 드로어
  const [flashAxis, setFlashAxis] = useState<Axis | null>(null);   // T-35 감정 변화 플래시
  const [tradeFlash, setTradeFlash] = useState<{ action: "buy" | "sell"; detail?: string } | null>(null);   // T-35 매매 배지(카드)
  const tradeFlashTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const prevEmoRef = useRef<Emotion | null>(null);
  const [dayReport, setDayReport] = useState<DayReportData | null>(null);   // T-33/T-34 취침+정산
  const dayLogRef = useRef<{ label: string; tag: "buy" | "sell" | "hold" }[]>([]);   // 하루 동작 로그(정산에 표시)
  const [report, setReport] = useState<api.DiagnosisReport | null>(null);   // T-47e 진단 리포트(엔딩 후)
  const pendingNextRef = useRef<EmoState | null>(null);
  const mapRef = useRef<MapBackgroundHandle>(null);
  const stateRef = useRef<EmoState | null>(null);
  const boardPickRef = useRef<((id: string) => void) | null>(null);
  const day = state?.day ?? -1;

  // 인트로: 시작 전 몇 초 뒤에 "click to start" 노출.
  useEffect(() => {
    if (started) return;
    const t = setTimeout(() => setCanStart(true), 2500);
    return () => clearTimeout(t);
  }, [started]);

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
    if (questionIndex < QUESTIONS.length - 1) {
      setQuestionIndex((i) => i + 1);
    } else {
      setStep(2);
    }
    return true;
  }, [answers, questionIndex]);

  // T-22/A — 하루 일과: 클론이 시간대별로 걷고, 그 도중 만남·게시판이 등장한다.
  // 게시판(그날 시장 이벤트)은 랜덤 밴드에 도착 → 반응 선택은 그 자리에서 받되,
  // 정산(choose: 감정·시장·리밸런싱 + day++)은 남은 하루를 다 걷고 **저녁에** 한다.
  // (사용자: "선택 후 남은 하루를 걷고" — 선택=하루 끝이 아니라 하루 중 반응.)
  useEffect(() => {
    if (day < 0) return;
    const s = stateRef.current;
    if (!s || s.is_over) { setBoard(null); setChain(null); return; }
    let cancelled = false;
    (async () => {
      setBoard(null); setChain(null); setDilemma(null);
      dayLogRef.current = [];   // 새 하루 시작 — 동작 로그 초기화
      // T-30c — 하루 시작에 캐시아웃 딜레마(발동 조건 충족 시 1회). 날짜는 안 넘어감.
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
          const pickedChoice = b.scenario.choices.find((c) => c.id === picked);
          pickedLabel = pickedChoice?.label ?? "";
          if (pickedLabel) {
            const pos = pickedChoice?.position ?? 0;
            dayLogRef.current.push({ label: pickedLabel, tag: pos >= TRADE_FX_MIN ? "buy" : pos <= -TRADE_FX_MIN ? "sell" : "hold" });
          }
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
          log: dayLogRef.current,
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

  useEffect(() => {
    if (state || step !== 1) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (["1", "2", "3", "4"].includes(e.key)) {
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
    const seed = Math.floor(Math.random() * 100000);
    // T-30 — 높음/중간/낮음 → 상대 가중치(백엔드가 합으로 정규화).
    const weights: Record<string, number> = {};
    CATEGORIES.forEach((c) => { weights[c] = LEVEL_WEIGHT[levels[c]]; });
    const s = await api.startEmo(answers, seed, 20, weights, name.trim());   // T-48f — 20일(표본 견고화)
    if (s) setRun(s);
    else setError("게임을 시작하지 못했어요. 잠시 후 다시 시도해 주세요.");
    setBusy(false);
  };

  // 만남(체인) 응답 — 걷기 도중. day 불변이라 일과 시퀀스 재실행 안 함.
  const resolveChain = async (id: string) => {
    const s = stateRef.current; if (!s) return;
    const cLabel = chain?.choices.find((c) => c.id === id)?.label ?? "";
    if (cLabel) dayLogRef.current.push({ label: cLabel, tag: "hold" });
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
  const showTradeFlash = (action: "buy" | "sell", detail?: string) => {
    setTradeFlash({ action, detail });
    if (tradeFlashTimer.current) clearTimeout(tradeFlashTimer.current);
    tradeFlashTimer.current = setTimeout(() => setTradeFlash(null), 1800);
  };

  // 게시판 반응 — 낮에 고름. 정산은 아니고(저녁에 함) 일과 시퀀스의 대기를 푼다.
  // 고른 반응의 position으로 매매 배지를 띄운다. 관망(-0.2)·소액 태움(0.1) 같은
  // **소극적 선택**엔 안 뜨게 결정적 매매(|position|≥0.25)만.
  const TRADE_FX_MIN = 0.25;
  // T-41 — 게시판 여론 미연시 넘기기: 글(post)을 한 명씩 보고 클릭으로 다음 글 →
  // 마지막 글 다음에 이벤트 요약+선택지가 뜬다(아래 advEvent board 분기).
  const advanceBoard = () => setBoardStep((s) => s + 1);
  const reactBoard = (id: string) => {
    const choice = board?.scenario.choices.find((c) => c.id === id);
    const pos = choice?.position ?? 0;
    if (pos >= TRADE_FX_MIN) showTradeFlash("buy", choice?.label);
    else if (pos <= -TRADE_FX_MIN) showTradeFlash("sell", choice?.label);
    boardPickRef.current?.(id);
  };
  // T-30c — 캐시아웃 딜레마 응답. 현금화(cash_out)=위험자산 매도 → 매매 배지.
  const resolveDilemma = (id: string) => {
    // 현금화·익절·소비 = 이익 실현(매도) → 매도 배지. (T-50d: take_profit·spend)
    if (id === "cash_out" || id === "take_profit" || id === "spend") {
      showTradeFlash("sell", dilemma?.choices.find((c) => c.id === id)?.label);
    }
    dilemmaPickRef.current?.(id);
  };

  // T-33/T-34 — 정산 리포트에서 "다음 날" → 다음 날로 진행(일과 시퀀스 재시작).
  const advanceDay = () => {
    const ns = pendingNextRef.current;
    pendingNextRef.current = null;
    setDayReport(null);
    if (ns) setRun(ns);
  };

  // ---------- 온보딩 위저드(T-29: 한 화면 한 목적 — 이름 → 진단 → 배분) ----------
  if (!state) {
    const diagnosisReady = QUESTIONS.every((q) => q.key in answers);
    const totalW = CATEGORIES.reduce((s, c) => s + LEVEL_WEIGHT[levels[c]], 0);
    const STEP_TITLE = ["이사 온 날", "투자 성향 진단", "성향 결과", "초기 자산 배분"];
    const currentQuestion = QUESTIONS[questionIndex];
    const currentAnswered = currentQuestion.key in answers;
    const progressPct = Math.round(((questionIndex + (currentAnswered ? 1 : 0)) / QUESTIONS.length) * 100);
    const goBack = () => {
      if (step === 1 && questionIndex > 0) { setQuestionIndex((i) => i - 1); return; }
      setStep((s) => Math.max(0, s - 1));
    };
    const goNext = () => {
      if (step === 1) {
        advanceQuestion();
        return;
      }
      setStep((s) => s + 1);
    };
    return (
      <main
        className="min-h-screen bg-pixel-path bg-cover bg-center flex items-center justify-center p-4"
        style={{
          backgroundImage:
            "linear-gradient(rgba(0,0,0,0.72),rgba(0,0,0,0.72)), url('/img/cover.png')",
        }}
      >
        {/* 타이틀 — 처음엔 화면 가운데 크게, 시작하면 좌상단으로 부드럽게 이동 */}
        <motion.img
          src="/img/title_image.png"
          alt="Market Village"
          className="fixed z-20 drop-shadow-[0_2px_8px_rgba(0,0,0,0.8)]"
          initial={false}
          animate={
            started
              ? { left: 16, top: 16, x: 0, y: 0, width: 150 }
              : { left: "50%", top: "45%", x: "-50%", y: "-50%", width: 500 }
          }
          transition={{ type: "tween", duration: 1.2, ease: [0.22, 1, 0.36, 1] }}
        />

        <AnimatePresence>
          {!started && (
            <motion.button
              type="button"
              aria-label="시작하기"
              disabled={!canStart}
              onClick={() => setStarted(true)}
              className="fixed inset-0 z-10 flex items-end justify-center translate-y-[-20%]"
              initial={{ opacity: 0 }}
              animate={{ opacity: canStart ? 1 : 0 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.4 }}
              style={{ pointerEvents: canStart ? "auto" : "none" }}
            >
              <motion.span
                className="text-lg font-medium tracking-[0.3em] text-white drop-shadow-[0_2px_8px_rgba(0,0,0,0.9)]"
                animate={{ opacity: [0.4, 1, 0.4] }}
                transition={{ duration: 1.6, repeat: Infinity, ease: "easeInOut" }}
              >
                CLICK TO START
              </motion.span>
            </motion.button>
          )}
        </AnimatePresence>

        {started && (
          <motion.div
            className="w-full max-w-xl pt-16"
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 1.2, duration: 0.55, ease: "easeOut" }}
          >
            <PixelPanel tone="wall" className="w-full max-w-xl p-6">
              {/* 진행 표시 */}
              <div className="flex items-center gap-1.5 mb-4">
                {[0, 1, 2, 3].map((i) => (
                  <div key={i} className={`h-1.5 flex-1 rounded-full ${i <= step ? "bg-black/70" : "bg-black/15"}`} />
                ))}
              </div>
              <div className="text-[11px] text-pixel-muted mb-1">{step + 1} / 4</div>
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
                    onKeyDown={(e) => { if (e.key === "Enter") setStep(1); }}
                  />
                </div>
              )}

              {/* STEP 1 — 진단(한 문항 한 화면) */}
              {step === 1 && (
                <div>
                  <div className="mb-4">
                    <div className="mb-1 flex items-center justify-between text-[11px] font-bold text-pixel-muted">
                      <span>{questionIndex + 1} / {QUESTIONS.length}</span>
                      <span>{progressPct}%</span>
                    </div>
                    <div className="h-2 rounded-full border-2 border-black bg-white overflow-hidden">
                      <div className="h-full bg-[#76d672]" style={{ width: `${progressPct}%` }} />
                    </div>
                  </div>
                  <div className="rounded-xl border-2 border-black bg-white p-4 shadow-pixel-sm">
                    <div className="text-[11px] font-black text-black/45">{currentQuestion.key}</div>
                    <div className="mt-1 text-[17px] font-black leading-snug">{currentQuestion.text}</div>
                    <div className="mt-4 grid gap-2">
                      {currentQuestion.options.map(([label, val], optionIndex) => (
                        <button
                          type="button"
                          key={label}
                          aria-label={`선택지 ${optionIndex + 1}: ${label}`}
                          className={`grid min-h-12 grid-cols-[1fr_auto] items-center gap-3 rounded-xl border-2 px-3 py-2 text-left text-[13px] font-extrabold shadow-pixel-sm ${answers[currentQuestion.key] === val
                            ? "border-black bg-yellow-300"
                            : "border-black/35 bg-pixel-wall hover:bg-white"
                            }`}
                          onClick={() => selectQuestionOption(optionIndex)}
                        >
                          <span>{label}</span>
                          <span className={`inline-flex h-5 min-w-5 items-center justify-center rounded-md px-1 text-[8px] leading-none border border-gray-400 text-gray-400`}>
                            {optionIndex + 1}
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* STEP 2 — 결과 카드 */}
              {step === 2 && (
                diagnosis ? (
                  <InvestmentTypeCard
                    diagnosis={diagnosis}
                    onCopy={() => setShareCopied(true)}
                    onReset={() => {
                      setAnswers({});
                      setDiagnosis(null);
                      setQuestionIndex(0);
                      setShareCopied(false);
                      setStep(1);
                    }}
                  />
                ) : (
                  <div className="rounded-xl border-2 border-black bg-white p-4 text-[13px] font-bold shadow-pixel-sm">
                    결과를 계산하는 중…
                  </div>
                )
              )}

              {/* STEP 3 — 배분 */}
              {step === 3 && (
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
                  <PixelButton size="lg" variant="ghost" className="shrink-0" onClick={goBack}>
                    ← 뒤로
                  </PixelButton>
                )}
                {step < 3 ? (
                  <PixelButton
                    size="lg" className="flex-1"
                    disabled={(step === 1 && !currentAnswered) || (step === 2 && (!diagnosisReady || !diagnosis))}
                    onClick={goNext}
                  >
                    {step === 1 && questionIndex < QUESTIONS.length - 1 ? "다음 문항 →" : "다음 →"}
                  </PixelButton>
                ) : (
                  <PixelButton size="lg" className="flex-1" disabled={busy} onClick={start}>
                    {busy ? "시작하는 중…" : "이사 온 날 →"}
                  </PixelButton>
                )}
              </div>
            </PixelPanel>
          </motion.div>
        )}
      </main>
    );
  }

  // ---------- 엔딩 ----------
  if (state.is_over && state.ending) {
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

          <PixelButton
            size="lg"
            className="w-full mt-6"
            onClick={() => {
              setState(null);
              setAnswers({});
              setQuestionIndex(0);
              setDiagnosis(null);
              setShareCopied(false);
              setReport(null);
              setStep(0);
            }}
          >
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

        {/* T-35 — 매매 체감 카드: 결정적 반응 직후 맵 위에 잠깐(1.8s). 선택 내용(라벨)까지 전달. */}
        {tradeFlash && (
          <div className="absolute inset-x-0 top-[16%] z-30 flex justify-center px-3 pointer-events-none">
            <div className={`rounded-xl shadow-lg px-4 py-2.5 max-w-[85vw] border-2 border-black/20 animate-pulse ${tradeFlash.action === "buy" ? "bg-rose-600/90" : "bg-sky-600/90"}`}>
              <div className="flex items-center gap-1.5 text-[14px] font-extrabold text-white">
                {tradeFlash.action === "buy" ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                {tradeFlash.action === "buy" ? "클론 매수" : "클론 매도"}
              </div>
              {tradeFlash.detail && (
                <div className="text-[12px] text-white/85 mt-0.5">{tradeFlash.detail}</div>
              )}
            </div>
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

      {/* 포트폴리오·감정 다이얼로그 — 빈칸 많은 사이드 드로어 대신 내용에 맞춰 뜨는 중앙 창 */}
      {showPortfolio && (
        <div className="absolute inset-0 z-20 bg-black/40 flex items-center justify-center p-4" onClick={() => setShowPortfolio(false)}>
          <div className="w-full max-w-sm max-h-[85vh] bg-pixel-path rounded-xl border-2 border-black/25 shadow-lg p-3 overflow-y-auto flex flex-col gap-2" onClick={(e) => e.stopPropagation()}>
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
    </main>
  );
}
