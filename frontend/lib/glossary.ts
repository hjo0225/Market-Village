// §2 — 코인 입문자용 용어 사전(정적). short=한 줄 뜻, effect=이 게임에서의 영향.
// 문구는 스펙 §2.2 표 그대로(수정 금지) — components/Term.tsx·wrapTerms가 이 사전을 참조한다.

export interface GlossaryEntry {
  short: string;
  effect: string;
}

export const GLOSSARY: Record<string, GlossaryEntry> = {
  "대장주": { short: "시장을 대표하는 제일 큰 코인(비트코인)", effect: "변동이 상대적으로 완만, 포트폴리오의 기둥" },
  "알트코인": { short: "비트코인 외의 코인들", effect: "대장주보다 크게 오르고 크게 빠짐" },
  "밈코인": { short: "유행과 커뮤니티 힘으로 움직이는 코인", effect: "급등급락이 가장 심함 — 감정도 같이 흔들림" },
  "스테이블코인": { short: "1달러에 고정되도록 설계된 코인", effect: "가격이 거의 안 움직이는 대피처" },
  "현금화": { short: "코인을 팔아 원화로 바꾸는 것", effect: "수익률 0%가 되는 대신 시장 밖으로 대피" },
  "리스크 비중": { short: "전체 자산 중 가격이 출렁이는 코인의 비율", effect: "높을수록 시장이 움직일 때 내 자산도 크게 움직임" },
  "리밸런스": { short: "자산 비율을 다시 맞추는 것", effect: "오늘의 선택이 내일의 리스크 비중을 바꿈" },
  "노출": { short: "시장 변동에 얼마나 영향받는 상태인가", effect: "노출이 크면 오르든 내리든 크게 겪음" },
  "지수": { short: "시작을 100으로 놓고 본 가격 흐름", effect: "110이면 시작보다 10% 오른 것" },
  "평가손익": { short: "아직 팔지 않은 상태의 이익/손실", effect: "팔기 전까지는 숫자일 뿐 — 감정은 벌써 반응함" },
  "익절": { short: "이익이 난 상태에서 파는 것", effect: "미루다 되돌림을 맞는 게 대표 함정" },
  "손절": { short: "손실을 확정하고 파는 것", effect: "계획된 손절은 방어, 패닉의 손절은 함정" },
  "존버": { short: "손실을 버티며 계속 보유하는 것", effect: "버티기가 전략일 때도, 회피일 때도 있음" },
  "물타기": { short: "떨어질 때 더 사서 평균 단가를 낮추는 것", effect: "확신이면 전략, 오기면 손실 확대" },
  "FOMO": { short: "나만 못 벌까 봐 조급해지는 마음", effect: "고점 추격 매수를 부르는 감정" },
  "패닉셀": { short: "급락에 놀라 던지듯 파는 것", effect: "바닥에서 파는 대표 패턴" },
  "관망": { short: "사지도 팔지도 않고 지켜보는 것", effect: "아무것도 안 하는 것도 선택 — 감정 소모는 있음" },
};

// 사전 키 목록. 길이 내림차순 — wrapTerms가 부분 문자열 충돌(예: "대장주"가 먼저
// 매칭돼야 하는데 더 짧은 다른 키가 먼저 걸리는 경우) 없이 가장 긴 키부터 시도하게 한다.
const GLOSSARY_KEYS = Object.keys(GLOSSARY).sort((a, b) => b.length - a.length);

export interface WrappedSegment {
  text: string;
  term: string | null;   // 매칭된 사전 키(있으면 Term으로 감싸야 함)
}

// §2.1 — 데이터 문자열(선택지 라벨 등)에서 사전 키의 "첫 등장만" 찾아 감싼다.
// 한 문장 최대 2개(밑줄 범벅 금지). 텍스트를 세그먼트 배열로 쪼개 반환 —
// 호출부(주로 Term.tsx가 아닌 렌더 코드)가 term이 있는 세그먼트만 <Term>으로 감싼다.
export function wrapTerms(text: string, maxTerms = 2): WrappedSegment[] {
  if (!text) return [{ text, term: null }];

  type Match = { start: number; end: number; term: string };
  const matches: Match[] = [];
  const usedRanges: [number, number][] = [];

  for (const key of GLOSSARY_KEYS) {
    if (matches.length >= maxTerms) break;
    const idx = text.indexOf(key);
    if (idx === -1) continue;
    const end = idx + key.length;
    // 이미 다른 매칭과 겹치면 스킵.
    const overlaps = usedRanges.some(([s, e]) => idx < e && end > s);
    if (overlaps) continue;
    matches.push({ start: idx, end, term: key });
    usedRanges.push([idx, end]);
  }

  if (matches.length === 0) return [{ text, term: null }];

  matches.sort((a, b) => a.start - b.start);
  const segments: WrappedSegment[] = [];
  let cursor = 0;
  for (const m of matches) {
    if (m.start > cursor) segments.push({ text: text.slice(cursor, m.start), term: null });
    segments.push({ text: text.slice(m.start, m.end), term: m.term });
    cursor = m.end;
  }
  if (cursor < text.length) segments.push({ text: text.slice(cursor), term: null });
  return segments;
}
