# 🎨 DESIGN.md — Market Village UI Design System

> 디자인 토큰 + 컴포넌트 규칙의 Single Source of Truth. UI 코드 작성 전 반드시 이 문서를 먼저 읽고, 정의된 토큰만 사용한다. 새 토큰이 필요하면 코드보다 이 문서를 먼저 수정한다.

> **출처·검증(2026-07-10)**: market_aquarium(참조 repo)에서 이식. 색 램프·형태·타이포(§1)를 우리 `frontend/tailwind.config.ts`·`app/globals.css`와 **전량 대조 완료 — 정정 hex 0개**(이미 이식돼 일치). §2 컴포넌트 사양은 실물과 대조해 드리프트를 표기했다.
> **관련 문서**: `.design-sync/conventions.md` = claude.ai/design 에이전트용 **descriptive**(빌드로 자동 검증) 슬라이스. 이 DESIGN.md = 사람용 **prescriptive** SSOT. 둘이 어긋나면 이 문서를 고치고 conventions는 재싱크로 재검증한다.

## 0. ✨ 핵심 원칙 (Core Principles)

- **폰트: Pretendard 고정.** 모든 UI 텍스트는 `Pretendard`(한글+라틴). 픽셀/비트맵 폰트는 쓰지 않는다.
- **모서리: 둥글게.** 카드·버튼·패널·모달은 둥근 모서리. 직각(0px)은 쓰지 않는다.
- **흰색 베이스.** UI는 전반적으로 흰색이 지배한다. 큰 면을 색으로 채우지 않는다.
- **테두리·카드 배경은 흑백만.** 카드/패널/인풋 등 표면 배경은 **흰색**, 테두리·스트로크·텍스트는 **검정(`#161616`)**. 표면/테두리에 색(그린·옐로)을 쓰지 않는다.
- **색은 포인트에만.** 그린(잔디)·옐로(흙길)는 **버튼·활성 상태·태그·상태 표시·배너 등 작은 강조 요소에만**. 표면이나 테두리에는 쓰지 않는다.
- **하이브리드 레트로.** Pretendard·둥근 모서리의 모던 베이스 + **검정 솔리드 드롭섀도우(블러 0)** 로 게임 감성을 약간 남긴다. (컴포넌트가 `Pixel*`로 명명된 이유 — 픽셀 폰트가 아니라 이 하드-섀도우 감성을 뜻한다.)
- **반드시 실제 데이터.** 목·하드코딩으로 "되는 것처럼" 보이게 만들지 않는다.

## 1. 🎨 글로벌 디자인 토큰 (Global Design Tokens)

> **테마: 흑백 카드 + 컬러 액센트, 2-Hue(그린+옐로).** 표면은 흰색, 라인은 검정. 강조·상태·아이콘만 그린·옐로 두 hue로.

### 1-0. 시스템 규칙 (Color System Rules)

1. **표면·테두리는 흑백만.** 카드/패널/헤더/인풋 배경 = 흰색. 테두리·텍스트·솔리드 섀도우 = 검정(`#161616`).
2. **색은 액센트 전용.** 그린·옐로는 버튼·활성 탭·태그·상태·배너 헤더 같은 **작은 요소**에만. 큰 면이나 라인에 쓰지 않는다.
3. **hue는 그린·옐로 두 가지뿐.** 빨강·파랑 등 새 hue 금지. 위계는 같은 hue의 명도/채도 단계로.
   - 예외: **시세 방향 표기**는 국내 관행상 상승=`text-rose-600`, 하락=`text-sky-600`을 쓴다(감정/브랜드 색이 아니라 데이터 부호 전용). `.design-sync/conventions.md`와 일치.
4. **회색은 보조로만.** 연한 그레이는 캡션/보조 텍스트·hover 하이라이트에만. 카드 배경이나 테두리로 쓰지 않는다.
5. **상태색은 색 하나에 의존 금지** — 반드시 아이콘 + 라벨을 함께 둔다.

### 1-1. 표면 전략 (Surface Strategy)

| 맥락                          | 표면(배경)        | 테두리          |
| ----------------------------- | ----------------- | --------------- |
| 모달·카드·패널·헤더·탭·인풋   | `paper #FFFFFF`   | `line #161616` 2px + 검정 솔리드 섀도우 |
| 휴대폰 베젤/기기 크롬(어두운 면) | `ink #161616`     | 없음            |
| 강조·활성·상태·태그·배너 헤더 | `green.*`/`yellow.*` (작은 면) | `line` 2px |

> 어두운 면은 **휴대폰 베젤·기기 크롬에만** 제한적으로 허용(블랙). 일반 콘텐츠 표면은 전부 흰색.

### 1-2. 색상 램프 (Color Ramps)

> 아래 hex는 `frontend/tailwind.config.ts`의 실제 값과 **전량 일치**(2026-07-10 대조).

#### GREEN 램프 — 잔디 (액센트 메인)

| 토큰명      | Hex       | 용도                                        |
| ----------- | --------- | ------------------------------------------- |
| `green.50`  | `#E8F8DC` | 태그/성공 칩 배경 (작은 면). `pixel.water` 별칭 동일 |
| `green.100` | `#B7EE8C` | 밝은 강조 칩                                |
| `green.200` | `#78F142` | 메인 액센트 / 성공(success) / 활성 채움. `pixel.grass` 별칭 동일 |
| `green.400` | `#4FA82A` | primary 버튼 hover                          |
| `green.600` | `#327A1C` | 성공/상승 텍스트, 정보(info). `pixel.greenText` 별칭 동일 |
| `green.800` | `#1E4D11` | 진한 그린 텍스트(필요 시)                   |
| `green.900` | `#143408` | 가장 진한 그린(거의 안 씀)                  |

#### YELLOW 램프 — 흙길 (보조 액센트)

| 토큰명       | Hex       | 용도                                       |
| ------------ | --------- | ------------------------------------------ |
| `yellow.50`  | `#FFF6D6` | 옅은 경고 칩 배경 (작은 면)                |
| `yellow.100` | `#FFE87C` | 밝은 옐로 칩                               |
| `yellow.200` | `#FFD23F` | 경고(warning) 강조                         |
| `yellow.400` | `#E0A41E` | secondary 강조 면                          |
| `yellow.600` | `#A8741A` | 강조(gold) 텍스트. `pixel.gold` 별칭 동일  |
| `yellow.800` | `#6E4B12` | 위험(danger) (번트 앰버, 흰글자 가능). `pixel.danger` 별칭 동일 |
| `yellow.900` | `#4A310B` | 가장 진한 옐로(거의 안 씀)                 |

> ⓘ `yellow.50/100/900`은 원본 DESIGN.md엔 없었으나 우리 tailwind에 존재 → SSOT 완전성 위해 추가(값=실제 코드).

#### 흑백 / 중립 (B&W & Neutral)

| 토큰명     | Hex       | 용도                                         |
| ---------- | --------- | -------------------------------------------- |
| `paper`/`wall`/`table`/`cloud` | `#FFFFFF` | 모든 카드·패널·헤더·인풋 표면 |
| `ink`      | `#161616` | 휴대폰 베젤/기기 크롬 (블랙)                 |
| `inkSoft`  | `#2A2D31` | 베젤 버튼/노치 액센트                        |
| `line`(`black`) | `#161616` | 테두리·텍스트·솔리드 섀도우 기본 (블랙) |
| `path`     | `#F2F4F7` | hover 하이라이트(작은 면). = `slate.100`     |
| `muted`    | `#6B7280` | 밝은 배경 위 캡션/보조 텍스트(그레이). = `slate.500` |
| `mutedDark`| `#AEB4BD` | 베젤 위 캡션 텍스트. = `slate.400`           |

> Tailwind `black` 토큰을 `#161616`로 매핑 → 기존 `border-black`/`text-black` 클래스가 그대로 흑백 라인이 된다.
> 보조 그레이 계열은 `slate.50~900` 램프로도 제공(`#F8FAFC`~`#161616`); `path`/`muted`/`mutedDark`는 그 중 100/500/400의 의미 별칭이다.

### 1-3. 상태색 (Status — 색+아이콘+라벨)

| 상태         | 토큰         | 전경 글자 | 아이콘(필수) |
| ------------ | ------------ | --------- | ------------ |
| 성공 success | `green.200`  | `black`   | ✓ check      |
| 정보 info    | `green.600`  | `paper`   | ⓘ info       |
| 경고 warning | `yellow.200` | `black`   | ⚠ alert      |
| 위험 danger  | `yellow.800` | `paper`   | ✕ stop       |

### 1-4. 형태 토큰 (Shape Tokens)

| 토큰              | 값                    | 용도                            |
| ----------------- | --------------------- | ------------------------------- |
| `radius.sm`       | `8px`                 | 칩·작은 버튼·인풋               |
| `radius.md`(기본) | `12px`                | **카드·패널·버튼 기본**         |
| `radius.lg`       | `16px`                | 모달·큰 패널                    |
| `radius.xl`~`3xl` | `20`/`24`/`28px`      | 휴대폰 화면/베젤 등 큰 곡률     |
| `radius.full`     | `9999px`              | 도트·아바타·pill 배지·태그      |
| `border`          | `2px solid #161616`   | 표면 기본 테두리 (블랙)         |
| `shadow.solid.sm` | `2px 2px 0 0 #161616` | 칩/작은 버튼 (`shadow-pixel-sm` / `.pixel-shadow-sm`) |
| `shadow.solid.md` | `3px 3px 0 0 #161616` | 카드/패널 (`shadow-pixel-md` / `.pixel-shadow`) |
| `shadow.solid.lg` | `5px 5px 0 0 #161616` | 모달 (`shadow-pixel-lg` / `.pixel-shadow-lg`) |
| `shadow.solid.phone` | `6px 6px 0 0 #161616` | 휴대폰 베젤/기기 프레임 (`shadow-phone`) |

> 그림자는 **솔리드 블록(블러 0) + 블랙**. 카드·버튼 12px, 모달 16px 둥글게. 소프트 섀도우·그라데이션 금지(게이지·프로그레스 등 의도적 예외만).
> ⓘ `shadow.solid.phone`은 원본에 없던 실코드 토큰(BoardOpinionFeed 폰 프레임용) → 추가.

### 1-5. 폰트 자원 (Font Resource)

- **Pretendard** (orioncactus/pretendard, OFL) — 한글+라틴 가변 산세리프.
- 로드: `app/globals.css`의 `@import`(jsDelivr CDN `pretendard@v1.3.9`), `font-family: 'Pretendard Variable','Pretendard', system-ui, sans-serif`.
- 안티앨리어싱 **켠다**(`-webkit-font-smoothing: antialiased`). 게임 스프라이트(`/assets/*`)만 `image-rendering: pixelated`.

### 1-6. 타이포그래피 (Typography)

| 토큰           | Size   | Weight  | Line Height | 용도                       |
| -------------- | ------ | ------- | ----------- | -------------------------- |
| `font.h1`      | `24px` | 700/800 | 1.4         | 대메뉴 타이틀, 모달 헤더   |
| `font.h2`      | `18px` | 700     | 1.4         | 섹션 타이틀, 카드 헤더     |
| `font.body`    | `14px` | 400     | 1.6         | 본문, 설명문, 인풋 값      |
| `font.button`  | `14px` | 700     | 1.2         | 버튼 내부 텍스트           |
| `font.caption` | `11px` | 400/700 | 1.4         | 캡션, 유저 ID, 상태 메시지 |

> 글자색: 흰 표면 위 → `black`(`#161616`) 또는 `muted`. 블랙 베젤 위 → `paper`(흰) 또는 `mutedDark`.

## 2. 🧱 컴포넌트 상세 사양 (Component Specifications)

> ✅ = 저장소에 존재하고 사양대로 구현됨. 컴포넌트 위치는 `frontend/components/`.

### 🔘 PixelButton ✅ (`components/pixel/PixelButton.tsx`)

- **모양**: `radius 10px`, `black` 2px 테두리 + 검정 솔리드 섀도우. Active 시 `translate(1px,1px)` + 그림자 제거.

| variant   | bg           | text    | 비고                       |
| --------- | ------------ | ------- | -------------------------- |
| primary   | `green.200`  | `black` | 메인 액션 (그린 액센트)    |
| secondary | `green.100`  | `black` | 보조 액션                  |
| danger    | `yellow.800` | `paper` | 파괴적 액션 + ✕ 아이콘     |
| ghost     | `paper`(흰)  | `black` | 약한 액션(흰 면 + 검정 라인) |

### 🟩 PixelPanel ✅ (`components/pixel/PixelPanel.tsx`)

- **모양**: `radius 12px`, `black` 2px, 검정 솔리드 섀도우.
- **tone**: `paper`/`wall`/`cloud`(흰 카드) / `ink`(블랙 베젤, 흰 글자) / `path`(연한 hover).

### 📱 BoardOpinionFeed ✅ (`components/emo/BoardOpinionFeed.tsx`)

> ⚠ 원본 DESIGN.md의 `BoardFeed`에 해당하는 실제 컴포넌트. 게시판(단톡방 여론)을 **실제 스마트폰처럼** 렌더.

- **기기 베젤**: `ink #161616`(블랙) 베젤 + 큰 곡률(`radius.xl`~`3xl`) + `shadow.solid.phone`. 측면 버튼.
- **상단**: 다이내믹 아일랜드(노치) + 상태바(시간·신호·와이파이·배터리).
- **화면**: 흰 앱 화면, 앱 헤더·탭(흰 면 + 검정 라인, 활성 탭만 그린), 피드 카드(흰 + 검정 라인 + 둥근 모서리).
- **하단**: 홈 인디케이터 pill.
- 데이터 props·폴링 계약은 바꾸지 않는다(표현만).

### 🪟 PixelModal ⛔ (미구현 — 필요 시 이 사양대로 신설)

> 현재 저장소에 컴포넌트 없음. 모달이 필요해지면 아래 사양을 기준으로 만든다(사양은 유효, 구현만 부재).

- **모양**: `radius 16px`, `black` 2px, 검정 솔리드 섀도우, 바디·헤더 흰색(헤더는 라인으로 구분). 팝 애니메이션.
- **오버레이**: 블랙 딤(`ink/60`). A11y `role="dialog"`, ESC/X 닫기.

## 3. 🤖 AI 작업 수칙 (AI Instructions)

1. **폰트 Pretendard 고정**, 픽셀/비트맵 폰트 금지.
2. **모서리 둥글게**: 카드·버튼 12/10px, 모달 16px. 직각 금지.
3. **표면·테두리는 흑백만**: 카드 배경=흰색, 테두리·텍스트·섀도우=검정. 표면/테두리에 색 금지.
4. **색은 액센트 전용**: 그린·옐로는 버튼·활성·태그·상태·배너 등 작은 요소에만. (시세 부호 rose/sky는 데이터 전용 예외.)
5. **어두운 면은 베젤/기기 크롬에만**(블랙). 그 외 표면은 전부 흰색.
6. **2-Hue 고정**: 그린·옐로 외 hue 금지(시세 부호 제외).
7. **토큰 우선**: 위 토큰을 Tailwind(`green.*`/`yellow.*`/`pixel.*`)·CSS 변수로 매핑해 사용. 임의 hex 금지.
8. **상태는 색+아이콘+라벨**, **스타일**은 검정 솔리드 드롭섀도우(블러 0)만.
9. **토큰 변경은 코드 아니라 이 문서 먼저.** 새 컴포넌트/컨벤션은 여기 반영 후, `.design-sync` 재싱크로 conventions.md·claude.ai/design DS를 갱신한다.
