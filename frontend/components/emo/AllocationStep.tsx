"use client";

import { CATEGORIES, CATEGORY_LABEL, Category, CatalogCoin } from "@/lib/emoApi";
import PixelButton from "@/components/pixel/PixelButton";
import Term from "@/components/Term";
import { LEVELS, LEVEL_WEIGHT, LEVEL_LABEL, CATEGORY_FLAVOR, CATEGORY_TERM } from "@/constants/emo";
import { LevelMap, Level } from "@/types/emo";

// 온보딩 STEP 3 — 초기 자산 배분. v3 §B — catalog가 있으면 카테고리 라벨을 실명 코인
// ("비트코인(BTC) — 대장주" 식)으로, 없으면(조회 실패) 기존 제네릭 라벨로 자연 폴백(I6).
export default function AllocationStep({ levels, catalog, onChange }: {
  levels: LevelMap;
  catalog: CatalogCoin[] | null;
  onChange: (cat: Category, lv: Level) => void;
}) {
  const totalW = CATEGORIES.reduce((s, c) => s + LEVEL_WEIGHT[levels[c]], 0);
  return (
    <div className="flex flex-col gap-2.5">
      {CATEGORIES.map((c: Category) => {
        const pct = totalW > 0 ? Math.round((LEVEL_WEIGHT[levels[c]] / totalW) * 100) : 0;
        const coin = catalog?.find((k) => k.category === c);
        const termKey = CATEGORY_TERM[c];
        return (
          <div key={c} className="flex items-center gap-3 text-[12px]">
            <span className="w-28 shrink-0 text-black leading-tight">
              {coin ? (
                <>
                  {coin.name}({coin.symbol})
                  <span className="block text-[10px] text-pixel-muted">
                    {termKey ? <Term term={termKey}>{CATEGORY_FLAVOR[c]}</Term> : CATEGORY_FLAVOR[c]}
                  </span>
                </>
              ) : (
                CATEGORY_LABEL[c]
              )}
            </span>
            <div className="flex gap-1 flex-1">
              {LEVELS.map((lv) => (
                <PixelButton
                  key={lv} size="sm"
                  variant={levels[c] === lv ? "primary" : "ghost"}
                  className="flex-1"
                  onClick={() => onChange(c, lv)}
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
  );
}
