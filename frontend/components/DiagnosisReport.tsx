"use client";

// T-47e — 엔딩 후 진단 리포트. 1층 '선언된 자아'(진단 유형) vs 2층 '실제 행동'
// (편향) 괴리를 보여준다. 데이터는 GET /emo/{id}/report(disposition_report.py).
import { DiagnosisReport as ReportData, CATEGORY_LABEL, Category } from "@/lib/emoApi";

const TYPE_DESC: Record<string, string> = {
  안정형: "한 푼도 잃지 않는 것이 목표. 원금 보전 최우선.",
  안정추구형: "안정을 우선하되 약간의 초과 수익은 노림.",
  위험중립형: "위험과 수익의 균형을 추구하는 중도.",
  적극투자형: "높은 수익 위해 상당한 위험을 감수.",
  공격투자형: "인생 역전을 노리며 전액 리스크도 불사.",
};

// T-48d — 타임라인 결정점 종류 라벨.
const KIND_LABEL: Record<string, string> = { scenario: "시장", place: "장소", chain: "만남" };

export default function DiagnosisReport({ report }: { report: ReportData | null }) {
  if (!report || !report.available) return null;
  const sa = report.self_awareness;
  const comparison = report.bias_comparison ?? [];
  return (
    <div className="mt-6 pt-5 border-t-2 border-black/10 flex flex-col gap-5">
      <h2 className="text-lg font-extrabold">투자 성향 리포트</h2>

      {/* A — 선언된 자아 */}
      <section>
        <div className="text-[11px] text-pixel-muted mb-1">당신이 스스로 진단한 유형</div>
        <div className="text-base font-extrabold">{report.declared_type}</div>
        <div className="text-[12px] text-pixel-muted">{TYPE_DESC[report.declared_type ?? ""] ?? ""}</div>
        {report.subdimension?.text && (
          <p className="mt-2 text-[12px] leading-relaxed border-l-2 border-black/10 pl-3">
            {report.subdimension.text}
          </p>
        )}
      </section>

      {/* D — 자기 인식 정확도(핵심 수치) */}
      {sa != null && (
        <section className="bg-black/5 rounded-lg p-3">
          <div className="text-[11px] text-pixel-muted mb-1">말과 행동의 일치도</div>
          <div className="flex items-end gap-2">
            <span className="text-3xl font-extrabold tabular-nums leading-none">{sa}</span>
            <span className="text-[12px] text-pixel-muted mb-0.5">/ 100</span>
          </div>
          <div className="mt-2 h-2 rounded-full bg-black/10 overflow-hidden">
            <div className="h-full bg-black/70" style={{ width: `${Math.max(0, Math.min(100, sa))}%` }} />
          </div>
        </section>
      )}

      {/* B — 선언 vs 실제 편향 */}
      {comparison.length > 0 && (
        <section>
          <div className="text-[11px] text-pixel-muted mb-2">선언한 성향 vs 실제 행동 (편향별)</div>
          <div className="flex flex-col gap-2.5">
            {comparison.map((b) => (
              <div key={b.axis}>
                <div className="flex justify-between text-[12px] font-bold">
                  <span>
                    {b.label}
                    {b.sample != null && (
                      <span className={`ml-1.5 text-[10px] font-normal ${b.low_sample ? "text-amber-600" : "text-pixel-muted"}`}>
                        n={b.sample}{b.low_sample ? "·참고" : ""}
                      </span>
                    )}
                  </span>
                  <span className="tabular-nums text-pixel-muted">예상 {b.expected ?? "-"} · 실제 {b.actual}</span>
                </div>
                <div className="mt-1 relative h-2 rounded-full bg-black/10 overflow-hidden">
                  <div className="absolute inset-y-0 left-0 rounded-full bg-black/30" style={{ width: `${b.expected ?? 0}%` }} />
                  <div className="absolute inset-y-0 left-0 rounded-full bg-rose-500/70" style={{ width: `${Math.max(0, Math.min(100, b.actual))}%` }} />
                </div>
              </div>
            ))}
          </div>
          <div className="mt-2 text-[10px] text-pixel-muted">회색=선언한 예상 · 빨강=실제 행동. 벌어질수록 자기 인식과 다르게 행동한 것.</div>
        </section>
      )}

      {/* T-48d — 인과 타임라인: 언제 무엇이 터졌나(편향 발현일만) */}
      {(report.timeline?.length ?? 0) > 0 && (
        <section>
          <div className="text-[11px] text-pixel-muted mb-2">언제 무엇이 터졌나</div>
          <div className="flex flex-col gap-1">
            {report.timeline!.map((t, i) => (
              <div key={i} className="flex items-center gap-2 text-[12px]">
                <span className="w-12 shrink-0 font-bold tabular-nums">Day {t.day + 1}</span>
                <span className="text-pixel-muted">{KIND_LABEL[t.kind] ?? t.kind}</span>
                <span className="ml-auto font-bold text-rose-600">{t.biases.join(" · ")}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* C — 서술(LLM 리치, 폴백=결정론 인사이트) */}
      {(() => {
        const lines = (report.narrative && report.narrative.length > 0) ? report.narrative : report.insights;
        return lines && lines.length > 0 ? (
          <section className="flex flex-col gap-2 bg-black/[0.03] rounded-lg p-3">
            {lines.map((s, i) => (
              <p key={i} className="text-[12.5px] leading-relaxed">{s}</p>
            ))}
          </section>
        ) : null;
      })()}

      {/* v3 §B — 블라인드 해제: 종목명은 배분 화면에서 이미 공개됐으므로, 리빌의
          핵심은 "시기"다. 헤드라인은 기간 공개("당신의 열흘은 사실 ____이었다"),
          종목명은 부제로 내림(T-49c 갱신). */}
      {(report.blind_reveal?.length ?? 0) > 0 && (
        <section className="bg-black/[0.03] rounded-lg p-3">
          <div className="text-[11px] text-pixel-muted mb-1">시기 공개</div>
          <div className="text-base font-extrabold mb-2">
            {report.blind_reveal_headline ? (
              <span className="text-rose-600">{report.blind_reveal_headline}</span>
            ) : (
              <>당신의 열흘은 사실 <span className="text-rose-600">{report.blind_reveal![0].period ?? report.blind_reveal![0].date}</span>이었다</>
            )}
          </div>
          <p className="text-[11.5px] text-pixel-muted mb-2">
            코인마다 서로 다른 실제 시기의 열흘을 지나왔다. 시기를 모른 채 내린 판단 — 그게 당신의 민낯이다.
          </p>
          <div className="flex flex-col gap-1 text-[12px]">
            {report.blind_reveal!.map((r) => (
              <div key={r.category} className="flex justify-between text-pixel-muted">
                <span>{CATEGORY_LABEL[r.category as Category] ?? r.category}</span>
                <span>{r.name}({r.symbol}) · {r.period ?? r.date}</span>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
