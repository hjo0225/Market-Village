# Build context is the repo root (see docker-compose.prod.yml) — the app
# needs the sibling `environment/` folder (map assets) and `backend.sim`
# absolute imports rooted at the repo root.
FROM python:3.10-slim

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/
COPY environment/ environment/
# T-313 — 루트 시드 파일: sim/news.py·social.py가 REPO_ROOT(=/app) 기준으로 읽는다.
# 빠지면 뉴스/게시판 엔드포인트가 FileNotFoundError 500(라이브에서 발각).
COPY news_pool.seed.json board_pool.seed.json ./

WORKDIR /app/backend

EXPOSE 8100
CMD ["python", "-m", "uvicorn", "market_live_server:app", "--host", "0.0.0.0", "--port", "8100"]
