"use client";

import { useMemo, useState } from "react";
import { MessageSquare, Sparkles, Users as UsersIcon, X } from "lucide-react";
import { PlanView, PlanBandOption, AXIS_LABEL, Axis, npcPortraitSrc, NPC_NAME } from "@/lib/emoApi";
import PixelPanel from "@/components/pixel/PixelPanel";
import PixelButton from "@/components/pixel/PixelButton";

// v2 §3.1 — Day 0 첫 편성 도움말(정적 2줄, 닫기 가능). 컴포넌트 상태로만 관리
// (저장 불필요) — 닫으면 그 세션 동안 다시 안 뜬다.
const FIRST_PLAN_HELP = [
  "첫 일과다. 행동력 안에서 오전·오후·저녁을 채워주자.",
  "어디서 시간을 보내는지가 마음을 만들고, 마음이 지갑을 지킨다.",
];

// §2.3 — 「오늘의 일과」 편성 화면. 오전/오후/저녁 3밴드에 장소를 배치(점심=게시판
// 고정), 행동력 예산(PLAN_BUDGET) 안에서 트레이드오프. 카드의 forecast는 백엔드가
// 실제 정산과 동일 소스로 계산해 내려준 값(I3) — 프론트는 화살표 크기로만 표현.

const BAND_ORDER = ["오전", "오후", "저녁"] as const;

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
      <div className="flex items-center justify-between">
        <span className="text-[13px] font-extrabold">{option.place}</span>
        <span className="text-[11px] font-bold bg-black/5 rounded px-1.5 py-0.5 tabular-nums">비용 {option.cost}</span>
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
  const remaining = plan.budget - used;

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

  return (
    <div className="fixed inset-0 z-40 bg-pixel-path flex items-center justify-center p-2 sm:p-4">
      <PixelPanel tone="cloud" className="w-full max-w-4xl h-full sm:h-auto sm:max-h-[92vh] flex flex-col p-4 sm:p-5 overflow-hidden">
        {/* 상단: Day N + 행동력 게이지 */}
        <div className="shrink-0 flex items-center justify-between flex-wrap gap-2 mb-1">
          <div>
            <div className="text-[11px] text-pixel-muted">{cloneName} · Day {plan.day + 1}</div>
            <h1 className="text-lg font-extrabold">오늘의 일과</h1>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-bold text-pixel-muted">행동력</span>
            <div className="w-32 h-3 bg-slate-200 rounded-full overflow-hidden border border-black/15">
              <div
                className={`h-full transition-all duration-300 ${remaining < 0 ? "bg-red-500" : "bg-pixel-grass"}`}
                style={{ width: `${Math.min(100, (used / Math.max(1, plan.budget)) * 100)}%` }}
              />
            </div>
            <span className={`text-[12px] font-extrabold tabular-nums ${remaining < 0 ? "text-red-600" : ""}`}>
              {used}/{plan.budget}
            </span>
          </div>
        </div>

        {/* v2 §1 — 아침 내레이션(데이 프레임): 정적 한 줄, Day N 아래 */}
        {plan.morning?.text && (
          <p className="shrink-0 text-[12px] text-pixel-muted italic mb-3">{plan.morning.text}</p>
        )}

        {/* v2 §3.1 — Day 0 첫 편성 도움말(정적 2줄, 닫기 가능) */}
        {showFirstPlanHelp && (
          <div className="shrink-0 mb-3 flex items-start gap-2 rounded-lg border-2 border-black/15 bg-amber-50 p-2.5">
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

        <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-[160px_1fr] gap-3 overflow-hidden">
          {/* 좌측: 밴드 슬롯 + 점심 고정 */}
          <div className="flex lg:flex-col gap-2 overflow-x-auto lg:overflow-visible shrink-0">
            {BAND_ORDER.map((band) => (
              <div key={band} className="min-w-[120px] lg:min-w-0 rounded-lg border-2 border-black/15 bg-black/[0.03] p-2">
                <div className="text-[11px] font-bold text-pixel-muted mb-0.5">{band}</div>
                <div className="text-[13px] font-extrabold truncate">{assignment[band] ?? "미배정"}</div>
              </div>
            ))}
            <div className="min-w-[120px] lg:min-w-0 rounded-lg border-2 border-dashed border-black/20 bg-black/[0.02] p-2">
              <div className="text-[11px] font-bold text-pixel-muted mb-0.5 inline-flex items-center gap-1">
                <MessageSquare className="w-3 h-3" />점심(고정)
              </div>
              <div className="text-[13px] font-extrabold truncate">{plan.fixed["점심"]?.label ?? "단톡방 확인"}</div>
            </div>
          </div>

          {/* 우측: 밴드별 장소 카드 그리드 */}
          <div className="min-h-0 overflow-y-auto flex flex-col gap-4 pr-1">
            {BAND_ORDER.map((band) => (
              <div key={band}>
                <div className="text-[12px] font-extrabold mb-1.5">{band}</div>
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                  {(bandsByName[band] ?? []).map((option) => (
                    <PlaceCard
                      key={option.place}
                      option={option}
                      selected={assignment[band] === option.place}
                      affordable={wouldAfford(band, option)}
                      onSelect={() => pickPlace(band, option)}
                      onPreview={() => setPreviewKey({ band, place: option.place })}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 하단 프리뷰 바 */}
        <div className="shrink-0 mt-3 rounded-lg border-2 border-black/15 bg-black/[0.03] p-2.5 min-h-[3.25rem]">
          {previewOption ? (
            <div className="flex flex-col gap-1">
              <div className="flex items-center gap-2">
                <span className="text-[12px] font-extrabold">{previewKey?.band} · {previewOption.place}</span>
                <ForecastArrows forecast={previewOption.forecast} />
              </div>
              <p className="text-[12px] text-pixel-muted leading-relaxed">{previewOption.flavor}</p>
            </div>
          ) : (
            <p className="text-[12px] text-pixel-muted">카드를 살펴보면 여기에 상세 예보가 표시돼요.</p>
          )}
        </div>

        {/* 하단 액션 */}
        <div className="shrink-0 flex gap-2 mt-3">
          <PixelButton size="lg" variant="ghost" onClick={onSkip} disabled={busy}>
            자동 편성
          </PixelButton>
          <PixelButton
            size="lg" className="flex-1"
            disabled={!canConfirm || busy}
            onClick={() => onConfirm(assignment)}
          >
            {busy ? "편성하는 중…" : "오늘 일과 확정 →"}
          </PixelButton>
        </div>
      </PixelPanel>
    </div>
  );
}
