import type { NextConfig } from "next";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  // The rewrite proxy gives up after 30s by default, which kills any question that
  // triggers the repair loop (each repair is another LLM call). Keep this above the
  // backend's own REQUEST_TIMEOUT_SECONDS so the backend is what decides to stop.
  experimental: { proxyTimeout: 180_000 },

  // Browser calls same-origin /api/*, Next forwards it to FastAPI. No CORS involved.
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${BACKEND_URL}/api/:path*` }];
  },
};

export default nextConfig;
