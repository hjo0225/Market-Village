/** @type {import('next').NextConfig} */
const BACKEND = process.env.BACKEND_ORIGIN || "http://127.0.0.1:8100";

const nextConfig = {
  async rewrites() {
    // 백엔드(FastAPI, :8100)로 프록시 — CORS 없이 같은 오리진처럼 fetch.
    return [
      { source: "/control/:path*", destination: `${BACKEND}/control/:path*` },
      { source: "/map", destination: `${BACKEND}/map` },
      { source: "/assets/:path*", destination: `${BACKEND}/assets/:path*` },
    ];
  },
};

module.exports = nextConfig;
