import path from "node:path";
import type { NextConfig } from "next";

/**
 * The API base URL is read at build time from NEXT_PUBLIC_API_URL.
 *
 * On the single-project Vercel layout it is "/api", which the root
 * vercel.json routes to the FastAPI serverless function, so the browser
 * never makes a cross-origin request in production.
 */
const nextConfig: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  turbopack: {
    root: path.resolve(__dirname),
  },
  experimental: {
    optimizePackageImports: ["lucide-react", "date-fns"],
  },
};

export default nextConfig;
