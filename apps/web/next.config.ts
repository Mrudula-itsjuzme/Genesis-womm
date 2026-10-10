import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    const core = process.env.CORE_API_URL || 'http://127.0.0.1:8000';
    return [{ source: '/api/v1/:path*', destination: `${core.replace(/\/$/, '')}/api/v1/:path*` }];
  },
  /* config options here */
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
