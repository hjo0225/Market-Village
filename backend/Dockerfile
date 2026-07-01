# Build context is the repo root (see docker-compose.prod.yml) — the app
# needs the sibling `environment/` folder (map assets) and `backend.sim`
# absolute imports rooted at the repo root.
FROM python:3.10-slim

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/
COPY environment/ environment/

WORKDIR /app/backend

EXPOSE 8100
CMD ["python", "-m", "uvicorn", "market_live_server:app", "--host", "0.0.0.0", "--port", "8100"]
