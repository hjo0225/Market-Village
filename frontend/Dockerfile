FROM node:20-slim AS builder
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ .
# T-311 — next.config.js의 rewrites는 standalone 빌드 시점에 라우트 매니페스트로
# 구워진다(런타임 env 무시). 빌드 ARG로 반드시 주입 — 없으면 127.0.0.1 기본값이
# 박혀 컨테이너 안에서 백엔드를 못 찾는다(라이브 API 전체 500의 원인이었음).
ARG BACKEND_ORIGIN=http://backend:8100
ENV BACKEND_ORIGIN=$BACKEND_ORIGIN
RUN npm run build

FROM node:20-slim AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
# standalone 출력은 public/을 포함하지 않는다 — 수동 복사 필수.
# 빠지면 map.html(지도 iframe)·favicon 등 public 정적 파일 전부 404.
COPY --from=builder /app/public ./public

EXPOSE 3000
CMD ["node", "server.js"]
