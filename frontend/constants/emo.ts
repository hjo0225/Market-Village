import { StoryCut } from "@/components/StoryScene";
import { Category } from "@/lib/emoApi";
import { Level, LevelMap, Question, QuestionHint } from "@/types/emo";

// §3.1/§3.2/§3.3 — 정적 스토리 씬 스크립트(원문 그대로, LLM 호출 없음·I5).
export const PROLOGUE_CUTS: StoryCut[] = [
  { bg: "dark", lines: ["어떤 판단은, 내가 한 게 아니라 내 기분이 한 것이었다."] },
  { lines: ["마켓 빌리지. 주민 전원이 코인을 하는 작은 마을.", "이곳에 당신을 닮은 클론이 이사를 온다."] },
  { lines: ["클론은 당신의 습관대로 기뻐하고, 당신의 습관대로 흔들린다.", "그러니 먼저 — 당신이 어떤 사람인지 알려주세요."] },
];
export const BRIDGE_CUTS = (cloneName: string): StoryCut[] => [
  { lines: [`……여기가 마켓 빌리지구나. 이삿짐이라곤 지갑 하나.`], speaker: cloneName },
  { lines: ["마을 사람들은 전부 코인을 한다. 단톡방은 하루 종일 울린다.", "카페의 동수, 광장의 재훈, 펍 구석의 만식…… 곧 다 알게 된다."] },
  { lines: ["당신이 해줄 일은 하나. 클론의 하루를 짜주는 것.", "어디서 시간을 보내는지가, 마음을 만든다. 마음이, 지갑을 지킨다."] },
  { lines: ["그럼 — 첫째 날."] },
];
export const ENDING_PRE_CUT: StoryCut[] = [
  { lines: ["열흘 남짓, 클론의 계절이 끝났다. 이제 거울을 볼 시간."] },
];
// v2 §3.2 — 첫 게시판 진입 컷(게임당 1회, 컴포넌트 상태로만 관리). 첫 board 노출 직전.
export const FIRST_BOARD_CUT: StoryCut[] = [
  { lines: ["점심. 단톡방이 울린다.", "이 마을에서 점심 메뉴보다 뜨거운 화제 — 오늘의 시장."] },
];
// v2 §3.3 — 반환점 컷(day == total_days//2, 게임당 1회). 그날 편성 화면 진입 전.
export const HALFWAY_CUTS = (cloneName: string): StoryCut[] => [
  { lines: ["벌써 절반이구나. 처음엔 알림음마다 심장이 뛰었는데."], speaker: cloneName },
  { lines: ["이제 어떤 알림은 그냥 지나가게 둔다. 그게 좋은 건지는, 끝에 가서 알겠지."] },
];

// T-30 · 초기 배분 UX — low1·med2·high3(백엔드가 합으로 정규화).
export const LEVELS: Level[] = ["low", "med", "high"];
export const LEVEL_WEIGHT: Record<Level, number> = { low: 1, med: 2, high: 3 };
export const LEVEL_LABEL: Record<Level, string> = { low: "낮음", med: "중간", high: "높음" };
export const DEFAULT_LEVELS: LevelMap = {
  large_stable: "med", mid_alt: "med", meme: "low", stable: "low", cash: "med",
};
// T-65 (5안) — 성향별 초기 배분 프리셋. 진단 직후 declared_type으로 배분 기본값을 미리
// 담아 "성향이 즉시 반영됐다"는 첫 체감을 준다(자유 수정 가능). 안전자산(stable/cash)은
// 안정형→공격형으로 단조 감소, 위험자산(meme/mid_alt)은 단조 증가. 공격형은 대장주 대신
// 알트/밈에 무게(large_stable=med, 🙋 council). 위험중립형 = DEFAULT_LEVELS.
export const ALLOCATION_PRESET: Record<string, LevelMap> = {
  안정형:     { large_stable: "low",  mid_alt: "low",  meme: "low",  stable: "high", cash: "high" },
  안정추구형: { large_stable: "med",  mid_alt: "low",  meme: "low",  stable: "high", cash: "med"  },
  위험중립형: { ...DEFAULT_LEVELS },
  적극투자형: { large_stable: "high", mid_alt: "med",  meme: "med",  stable: "low",  cash: "low"  },
  공격투자형: { large_stable: "med",  mid_alt: "high", meme: "high", stable: "low",  cash: "low"  },
};
// v3 §B — 배분 화면 실명 코인 카드의 성격 한 줄("대장주"/"급등급락" 식).
export const CATEGORY_FLAVOR: Record<Category, string> = {
  large_stable: "대장주", mid_alt: "중견 알트", meme: "급등급락", stable: "안정적 페그", cash: "시장 밖 현금",
};
// §2.1 — 배분 화면 카테고리별 용어 사전 키(있으면 라벨에 Term 적용).
export const CATEGORY_TERM: Partial<Record<Category, string>> = {
  large_stable: "대장주", mid_alt: "알트코인", meme: "밈코인",
};

// 성향분석.md — 전국투자자교육협의회 '투자 성향 진단표' 7문항을 코인 맥락으로 재구성.
// 값=문항별 가중 점수(문항 내 유일). 백엔드 disposition.diagnose가 점수로 선택지를 역참조.
export const QUESTIONS: Question[] = [
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

// 코인을 모르는 사용자를 위한 문항별 친절 설명(정보 아이콘 다이얼로그).
export const QUESTION_HINTS: Record<string, QuestionHint> = {
  Q1: { title: "예금 vs 코인", text: "예금은 원금이 보장되는 안전한 저축이고, 코인은 오르면 크게 벌지만 떨어지면 원금을 잃을 수 있어요. 둘에 얼마씩 나눌지로 위험을 얼마나 감수하는지 봅니다." },
  Q2: { title: "투자 기간", text: "이 돈을 언제 다시 써야 하는지예요. 오래 묻어둘수록 가격이 출렁여도 회복을 기다릴 여유가 생깁니다." },
  Q3: { title: "적금 vs 코인 적립", text: "매달 버는 돈 중 안전한 적금과 코인에 각각 얼마를 넣을지예요. 꾸준한 습관에서 위험 성향이 드러납니다." },
  Q4: { title: "안전성·유동성·수익성", text: "안전성 = 원금을 잃지 않기, 유동성 = 필요할 때 바로 현금으로 바꾸기, 수익성 = 더 많이 벌기. 무엇을 먼저 챙기는지 순서로 성향을 봅니다." },
  Q5: { title: "자산 종류", text: "스테이블코인은 가격이 거의 안 움직이는 안전 자산, 우량 코인(비트코인·이더리움)은 대표주자, 알트·신규 코인은 급등급락이 심한 코인이에요." },
  Q6: { title: "분산 vs 집중", text: "분산은 여러 자산에 나눠 담아 시장 평균만큼 안정적으로, 집중은 손실 위험을 안고 평균보다 높은 수익을 노리는 방식이에요." },
  Q7: { title: "손실 감내도", text: "투자한 원금이 줄어드는 걸 어디까지 견딜 수 있는지예요. 예를 들어 100만 원을 넣고 20% 손실이면 20만 원이 줄어든 상태입니다." },
};

// 게시판 반응에서 결정적 매매로 볼 최소 |position|(미만은 소극적 → 배지 안 뜸).
export const TRADE_FX_MIN = 0.25;
// 코인 매매 대상 카테고리(현금 제외).
export const TRADE_CATS: Category[] = ["large_stable", "mid_alt", "meme", "stable"];
