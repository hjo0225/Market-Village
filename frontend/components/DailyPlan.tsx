"use client";

import { useMemo, useState } from "react";
import { MessageSquare, Sparkles, Users as UsersIcon, X, Check } from "lucide-react";
import { PlanView, PlanBandOption, AXIS_LABEL, Axis, npcPortraitSrc, NPC_NAME } from "@/lib/emoApi";
import PixelPanel from "@/components/pixel/PixelPanel";
import PixelButton from "@/components/pixel/PixelButton";

// v2 §3.1 — Day 0 첫 편성 도움말(정적 2줄, 닫기 가능). 컴포넌트 상태로만 관리
// (저장 불필요) — 닫으면 그 세션 동안 다시 안 뜬다.
const FIRST_PLAN_HELP = [
  "첫 일과다. 행동력 안에서 오전·오후·저녁을 채워주자.",
  "어디서 시간을 보내는지가 마음을 만들고, 마음이 지갑을 지킨다.",
];

// §1.3 — 「오늘의 일과」 편성 화면. 위저드 3스텝(오전→오후→저녁), 각 스텝은 해당
// 밴드의 옵션 카드만 보여준다. 점심(게시판)은 오전·오후 사이 고정 칩으로만 표시.
// 카드의 forecast는 백엔드가 실제 정산과 동일 소스로 계산해 내려준 값(I3) — 프론트는
// 화살표 크기로만 표현. §1.2(activity_id/activity_name)는 옵셔널 — 없으면(구버전
// 폴백) 기존처럼 장소명만 헤드라인으로 표시(I6).

const BAND_ORDER = ["오전", "오후", "저녁"] as const;
type Band = (typeof BAND_ORDER)[number];

function ForecastArrows({ forecast }: { forecast: Record<string, number> }) {
  const entries = Object.entries(forecast).filter(([, v]) => v !== 0);
  if (entries.length === 0) return <span className="text-[11px] text-pixel-muted">변화 없음</span>;
  return (
    <div className="flex flex-wrap gap-x-2 gap-y-0.5">
      {entries.map(([axis, v]) => {
        const mag = Math.min(3, Math.max(1, Math.round(Math.abs(v))));
        const up = v > 0;
        const arrows = (up ? "▲" : "▼").repeat(mag);
        return (
          <span
            key={axis}
            className={`inline-flex items-center gap-0.5 text-[11px] font-bold ${up ? "text-rose-600" : "text-sky-600"}`}
            title={`${AXIS_LABEL[(axis as Axis)] ?? axis} ${up ? "+" : ""}${v}`}
          >
            {AXIS_LABEL[(axis as Axis)] ?? axis}{arrows}
          </span>
        );
      })}
    </div>
  );
}

function BadgeChip({ badge }: { badge: string }) {
  if (badge === "npc") return (
    <span className="inline-flex items-center gap-0.5 text-[10px] font-bold text-emerald-700 bg-emerald-100 rounded-full px-1.5 py-0.5">
      <UsersIcon className="w-2.5 h-2.5" />만남
    </span>
  );
  if (badge === "dilemma") return (
    <span className="inline-flex items-center gap-0.5 text-[10px] font-bold text-amber-700 bg-amber-100 rounded-full px-1.5 py-0.5">
      <Sparkles className="w-2.5 h-2.5" />이벤트?
    </span>
  );
  return (
    <span className="inline-flex items-center gap-0.5 text-[10px] font-bold text-slate-600 bg-slate-100 rounded-full px-1.5 py-0.5">
      조용함
    </span>
  );
}

// §1.1 — 잔여 행동력보다 비용이 큰 카드는 흐리게 + "행동력 부족" 배지(예산 초과
// 에러가 아니라 잔여 부족으로 표현).
function InsufficientBadge() {
  return (
    <span className="inline-flex items-center gap-0.5 text-[10px] font-bold text-red-700 bg-red-100 rounded-full px-1.5 py-0.5">
      행동력 부족
    </span>
  );
}

function PlaceCard({
  option, selected, affordable, onSelect, onPreview,
}: {
  option: PlanBandOption;
  selected: boolean;
  affordable: boolean;
  onSelect: () => void;
  onPreview: () => void;
}) {
  const shownNpcs = option.npcs.slice(0, 3);
  // §1.2 — activity_name이 있으면 헤드라인(활동명) + 장소명 부제. 없으면(구버전
  // 폴백) 기존처럼 장소명만 헤드라인(I6).
  const headline = option.activity_name ?? option.place;
  const showPlaceSubline = !!option.activity_name;
  return (
    <button
      type="button"
      disabled={!affordable && !selected}
      onClick={onSelect}
      onMouseEnter={onPreview}
      onFocus={onPreview}
      className={`text-left rounded-lg border-2 p-2.5 flex flex-col gap-1.5 transition-colors
        ${selected ? "border-black bg-pixel-grass/30" : "border-black/15 bg-white hover:border-black/40"}
        disabled:opacity-40 disabled:cursor-not-allowed`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <span className="text-[13px] font-extrabold block truncate">{headline}</span>
          {showPlaceSubline && (
            <span className="text-[10.5px] text-pixel-muted block truncate">{option.place}</span>
          )}
        </div>
        <div className="shrink-0 flex flex-col items-end gap-0.5">
          <span className="text-[11px] font-bold bg-black/5 rounded px-1.5 py-0.5 tabular-nums">비용 {option.cost}</span>
          {!affordable && !selected && <InsufficientBadge />}
        </div>
      </div>
      <ForecastArrows forecast={option.forecast} />
      <div className="flex items-center justify-between mt-0.5">
        <div className="flex -space-x-2">
          {shownNpcs.map((n) => {
            const src = npcPortraitSrc(n.npc_id);
            return src ? (
              <img
                key={n.npc_id}
                src={src}
                alt={n.name || NPC_NAME[n.npc_id] || n.npc_id}
                className="w-8 h-8 rounded-full border-2 border-white object-cover bg-slate-200 [image-rendering:pixelated]"
              />
            ) : (
              <span
                key={n.npc_id}
                className="w-8 h-8 rounded-full border-2 border-white bg-slate-400 text-white text-[11px] font-bold flex items-center justify-center"
              >
                {(n.name || n.npc_id).charAt(0)}
              </span>
            );
          })}
        </div>
        <div className="flex gap-1">
          {option.badges.map((b) => <BadgeChip key={b} badge={b} />)}
        </div>
      </div>
    </button>
  );
}

// §1.3 — 상단 고정 바: 밴드 진행 표시 점(오전●–오후○–저녁○) + 남은 행동력 n/5 +
// 지금까지 고른 요약 칩(탭하면 해당 스텝으로 이동).
function ProgressDots({ stepIndex }: { stepIndex: number }) {
  return (
    <div className="flex items-center gap-1.5">
      {BAND_ORDER.map((band, i) => (
        <span key={band} className="flex items-center gap-1">
          <span
            className={`inline-block w-2.5 h-2.5 rounded-full border-2 border-black
              ${i < stepIndex ? "bg-black" : i === stepIndex ? "bg-pixel-grass" : "bg-white"}`}
            aria-hidden
          />
          <span className={`text-[11px] font-bold ${i === stepIndex ? "text-black" : "text-pixel-muted"}`}>{band}</span>
          {i < BAND_ORDER.length - 1 && <span className="text-pixel-muted mx-0.5">–</span>}
        </span>
      ))}
    </div>
  );
}

export default function DailyPlan({
  plan,
  cloneName,
  onConfirm,
  onSkip,
  busy = false,
}: {
  plan: PlanView;
  cloneName: string;
  onConfirm: (assignment: Record<string, string>) => void;
  onSkip: () => void;
  busy?: boolean;
}) {
  const [assignment, setAssignment] = useState<Record<string, string>>({});
  const [previewKey, setPreviewKey] = useState<{ band: string; place: string } | null>(null);
  const [helpDismissed, setHelpDismissed] = useState(false);
  const [stepIndex, setStepIndex] = useState(0);   // §1.3 — 위저드 스텝(0=오전, 1=오후, 2=저녁)
  const showFirstPlanHelp = plan.day === 0 && !helpDismissed;

  const bandsByName = useMemo(() => {
    const m: Record<string, PlanBandOption[]> = {};
    plan.bands.forEach((b) => { m[b.band] = b.options; });
    return m;
  }, [plan]);

  const used = useMemo(
    () => BAND_ORDER.reduce((sum, band) => {
      const place = assignment[band];
      const opt = bandsByName[band]?.find((o) => o.place === place);
      return sum + (opt?.cost ?? 0);
    }, 0),
    [assignment, bandsByName],
  );
  const remaining = plan.budget - used;   // §1.1 — 잔여 행동력(0-깎는 방향으로 표기)

  const previewOption = previewKey ? bandsByName[previewKey.band]?.find((o) => o.place === previewKey.place) : null;

  const allAssigned = BAND_ORDER.every((b) => !!assignment[b]);
  const canConfirm = allAssigned && used <= plan.budget;

  const pickPlace = (band: string, option: PlanBandOption) => {
    setAssignment((a) => {
      const next = { ...a };
      if (next[band] === option.place) { delete next[band]; return next; }
      next[band] = option.place;
      return next;
    });
  };

  const wouldAfford = (band: string, option: PlanBandOption) => {
    if (assignment[band] === option.place) return true;
    const currentForBand = bandsByName[band]?.find((o) => o.place === assignment[band]);
    const usedWithoutBand = used - (currentForBand?.cost ?? 0);
    return usedWithoutBand + option.cost <= plan.budget;
  };

  const currentBand: Band = BAND_ORDER[stepIndex];
  const isLastStep = stepIndex === BAND_ORDER.length - 1;
  const currentBandAssigned = !!assignment[currentBand];

  const goToStep = (i: number) => setStepIndex(Math.max(0, Math.min(BAND_ORDER.length - 1, i)));
  const goNext = () => { if (!isLastStep) goToStep(stepIndex + 1); };

  return (
    <div className="fixed inset-0 z-40 bg-black flex items-center justify-center p-2 sm:p-4 overflow-hidden">
      {/* 일과 편성 배경 — 컷씬(클론 집 고정 카메라) 위에 패널이 뜬다. */}
      <iframe
        src={`/map.html?mode=cutscene&name=${encodeURIComponent(cloneName)}`}
        title="마을 배경"
        aria-hidden
        className="absolute inset-0 h-full w-full border-0 pointer-events-none"
      />
      <div className="absolute inset-0 bg-black/55 pointer-events-none" />
      <PixelPanel tone="cloud" className="relative z-10 w-full max-w-4xl h-full sm:h-auto sm:max-h-[92vh] flex flex-col p-4 sm:p-5 overflow-hidden">
        {/* 상단: Day N */}
        <div className="shrink-0 flex items-center justify-between flex-wrap gap-2 mb-1">
          <div>
            <div className="text-[11px] text-pixel-muted">{cloneName} · Day {plan.day + 1}</div>
            <h1 className="text-lg font-extrabold">오늘의 일과</h1>
          </div>
        </div>

        {/* v2 §1 — 아침 내레이션(데이 프레임): 정적 한 줄, Day N 아래 */}
        {plan.morning?.text && (
          <p className="shrink-0 text-[12px] text-pixel-muted italic mb-2">{plan.morning.text}</p>
        )}

        {/* v2 §3.1 — Day 0 첫 편성 도움말(정적 2줄, 닫기 가능) */}
        {showFirstPlanHelp && (
          <div className="shrink-0 mb-2 flex items-start gap-2 rounded-lg border-2 border-black/15 bg-amber-50 p-2.5">
            <div className="flex-1 flex flex-col gap-0.5">
              {FIRST_PLAN_HELP.map((line, i) => (
                <p key={i} className="text-[12px] font-bold text-amber-900 leading-relaxed">{line}</p>
              ))}
            </div>
            <button
              type="button"
              onClick={() => setHelpDismissed(true)}
              aria-label="도움말 닫기"
              className="shrink-0 text-amber-900/60 hover:text-amber-900"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* §1.3 — 상단 고정 바: 밴드 진행 점 + 남은 행동력 + 점심 고정 칩 + 요약 칩 */}
        <div className="shrink-0 rounded-lg border-2 border-black/15 bg-black/[0.03] p-2.5 mb-3 flex flex-col gap-2">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <ProgressDots stepIndex={stepIndex} />
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-bold text-pixel-muted">남은 행동력</span>
              <div className="w-24 h-3 bg-slate-200 rounded-full overflow-hidden border border-black/15">
                <div
                  className={`h-full transition-all duration-300 ${remaining < 0 ? "bg-red-500" : "bg-pixel-grass"}`}
                  style={{ width: `${Math.min(100, Math.max(0, (remaining / Math.max(1, plan.budget)) * 100))}%` }}
                />
              </div>
              <span className={`text-[12px] font-extrabold tabular-nums ${remaining < 0 ? "text-red-600" : ""}`}>
                {Math.max(0, remaining)}/{plan.budget}
              </span>
            </div>
          </div>

          {/* 요약 칩: 탭하면 해당 스텝으로 이동. 점심(게시판)은 오전→오후 사이 고정 칩. */}
          <div className="flex items-center gap-1.5 flex-wrap">
            {BAND_ORDER.map((band, i) => {
              const place = assignment[band];
              const opt = bandsByName[band]?.find((o) => o.place === place);
              const label = opt?.activity_name ?? place;
              return (
                <div key={band} className="flex items-center gap-1.5">
                  <button
                    type="button"
                    onClick={() => goToStep(i)}
                    className={`inline-flex items-center gap-1 text-[11px] font-bold rounded-full px-2 py-1 border-2 transition-colors
                      ${i === stepIndex ? "border-black bg-pixel-grass/40" : "border-black/15 bg-white hover:border-black/40"}`}
                  >
                    {place && <Check className="w-3 h-3 text-emerald-600" />}
                    <span className="text-pixel-muted">{band}</span>
                    <span>{label ?? "미배정"}</span>
                  </button>
                  {/* 점심(게시판) 고정 칩 — 오전과 오후 스텝 사이에만 표시 */}
                  {band === "오전" && (
                    <span className="inline-flex items-center gap-1 text-[11px] font-bold rounded-full px-2 py-1 border-2 border-dashed border-black/20 bg-black/[0.02] text-pixel-muted">
                      <MessageSquare className="w-3 h-3" />
                      점심(고정) · {plan.fixed["점심"]?.label ?? "단톡방 확인"}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* 본문: 현재 스텝(밴드)의 옵션 카드만 표시 */}
        <div className="flex-1 min-h-0 overflow-y-auto pr-1">
          <div className="text-[13px] font-extrabold mb-1.5">{currentBand}</div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
            {(bandsByName[currentBand] ?? []).map((option) => (
              <PlaceCard
                key={option.place}
                option={option}
                selected={assignment[currentBand] === option.place}
                affordable={wouldAfford(currentBand, option)}
                onSelect={() => pickPlace(currentBand, option)}
                onPreview={() => setPreviewKey({ band: currentBand, place: option.place })}
              />
            ))}
          </div>
        </div>

        {/* 하단 프리뷰 바 */}
        <div className="shrink-0 mt-3 rounded-lg border-2 border-black/15 bg-black/[0.03] p-2.5 min-h-[3.25rem]">
          {previewOption ? (
            <div className="flex flex-col gap-1">
              <div className="flex items-center gap-2">
                <span className="text-[12px] font-extrabold">
                  {previewKey?.band} · {previewOption.activity_name ?? previewOption.place}
                </span>
                <ForecastArrows forecast={previewOption.forecast} />
              </div>
              <p className="text-[12px] text-pixel-muted leading-relaxed">{previewOption.flavor}</p>
            </div>
          ) : (
            <p className="text-[12px] text-pixel-muted">카드를 살펴보면 여기에 상세 예보가 표시돼요.</p>
          )}
        </div>

        {/* 하단 액션: 자동 편성(항상 가능) + 스텝 이동/확정 */}
        <div className="shrink-0 flex gap-2 mt-3">
          <PixelButton size="lg" variant="ghost" onClick={onSkip} disabled={busy}>
            자동 편성
          </PixelButton>
          {stepIndex > 0 && (
            <PixelButton size="lg" variant="ghost" onClick={() => goToStep(stepIndex - 1)} disabled={busy}>
              ← 이전
            </PixelButton>
          )}
          {!isLastStep ? (
            <PixelButton
              size="lg" className="flex-1"
              disabled={!currentBandAssigned || busy}
              onClick={goNext}
            >
              다음 →
            </PixelButton>
          ) : (
            <PixelButton
              size="lg" className="flex-1"
              disabled={!canConfirm || busy}
              onClick={() => onConfirm(assignment)}
            >
              {busy ? "편성하는 중…" : "이대로 하루 시작"}
            </PixelButton>
          )}
        </div>
      </PixelPanel>
    </div>
  );
}
