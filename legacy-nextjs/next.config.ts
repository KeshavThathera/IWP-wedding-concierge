import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: { unoptimized: true },
  // Lets a second local dev server run without sharing the .next build folder.
  distDir: process.env.NEXT_DIST_DIR || ".next",
};

export default nextConfig;
