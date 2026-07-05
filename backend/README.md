# Market Village — Simulation Backend

`market_live_server.py`가 유일한 게임 API 서버다. `sim/game_run.py`의 `GameRun`이
유일한 게임 경로(§12.4) — 전날밤(회피) → 아침(뉴스 3지선다) → 위기(개입 A/B/C·
저항판정) → 정산을 하루씩 진행하고, 회차(NG+)를 재현·비교한다. Next.js
`frontend/`의 `/play`가 이 API를 소비한다.

## Setup

```bash
cd backend
python -m pip install -r requirements.txt
```

LLM은 표현 계층(대사·독백)에만 쓰이고 수치 결정에는 영향을 주지 않는다. 키가
없으면 오프라인 결정론 템플릿으로 자동 폴백한다(과금 없음, 플레이 가능):

```bash
export OPENROUTER_API_KEY=sk-or-...
```

## MongoDB (선택)

게임 세션 영속화(`sim/db.py`)는 MongoDB를 시도하고 실패하면 인메모리로
폴백한다 — 로컬 개발에는 MongoDB가 **필수 아님**.

```bash
docker compose up -d          # MongoDB 27018 포트 (선택)
```

환경변수로 오버라이드 가능:
- `MONGO_URI`, `MONGO_DB`(기본 `market_village`)
- `MARKET_DISABLE_DB=1`로 DB 시도 자체를 끄고 인메모리만 사용

## Run

```bash
cd backend
python -m uvicorn market_live_server:app --port 8100
```

Windows에서는 PowerShell/cmd 사용 권장(Git Bash는 소켓 문제로 안 뜰 수 있음).

## Test

```bash
cd backend
python -m pytest -q
```

전부 오프라인·결정론(LLM 키·네트워크·MongoDB 불요). `conftest.py`가
`MARKET_DISABLE_LLM=1`을 자동 설정해 테스트는 LLM을 실호출하지 않는다.

## Endpoints

주요 경로 — 전체 목록은 `market_live_server.py`의 `@app.get/post` 참고.

| Method | Path | 역할 |
|---|---|---|
| POST | `/control/game/start` | 새 회차(GameRun) 시작 |
| GET | `/control/game/state` | 현재 회차 상태 |
| GET | `/control/game/news` | 아침 뉴스 3지선다 |
| POST | `/control/game/day/avoid` | 전날밤 회피 |
| POST | `/control/game/day/designate` | 전날밤 대화 상대 지정(T-272a) |
| POST | `/control/game/day/advance` | 하루 진행(개입 A/B/C 포함) |
| GET | `/control/game/day/scene` | 정산 연출 |
| GET | `/control/game/card` | 결과 카드 |
| POST | `/control/game/newrun` | 새 회차(NG+) |
| GET | `/control/game/compare` | 회차 비교(거울) |
| GET | `/control/interview/next` / POST `/answer` | 인터뷰 |
| GET | `/map` | Phaser 맵 뷰어(배경 연출, `/control/game/day/{home,walk}` 좌표 브릿지) |

## Module map (`sim/`)

| File | Role |
|---|---|
| `models.py` | 공유 pydantic 데이터 계약(단일 소스) |
| `llm.py` | LLM 클라이언트 + 오프라인 결정론 폴백 |
| `db.py` | 게임 세션 영속화(MongoDB, 실패 시 인메모리) |
| `game_run.py` | 하루씩 진행 가능한 회차 세션(GameRun) |
| `run_loop.py` | 30일 batch 실행 + `step_day` 공유 코어 |
| `crisis_day.py` | 하루치 결정 파이프라인 조립 |
| `traps.py` / `trap_pipeline.py` | 6함정 분류·트리거·판정 |
| `resistance.py` | 개입 전략 A/B/C + 저항식 |
| `news.py` | 뉴스 3지선다 |
| `clone_spec.py` / `clone_stats.py` | 인터뷰 → 클론 스펙 + 표시 4스탯 |
| `fate_line.py` | 고정 운명선(블라인드 과거 데이터) + 가격 하이브리드 |
| `trade.py` | 가격수용자 회계 |
| `runs.py` | 회차(NG+) 저장 + 비교 |
| `result_card.py` | 결과 카드 평가 |
| `day_loop.py` | 8슬롯 하루·일과 셔플 |
| `avoidance.py` | 전날밤 회피 |
| `social.py` | 설득/FGI 개입 |
| `sentiment.py` | 감정 기여도 계산 |
| `presentation.py` | 엔진 결정 → 연출명령+대사 |
| `interview.py` / `interview_llm.py` | 인터뷰 질문·클론 생성 |
| `tuning.py` | 전 수치 상수 단일 소스 |

## Frontend

```bash
cd frontend
npm install
npm run dev                          # http://localhost:3000/play
```
