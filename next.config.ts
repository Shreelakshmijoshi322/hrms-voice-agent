import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Allow the same existing voice app to run on two local ports when the
  // integrated HRMS UI and the standalone demo are both being previewed.
  distDir: process.env.NEXT_DIST_DIR ?? ".next",
  // Keep the development route indicator out of the embedded voice UI.
  // Next.js still reports compile/runtime errors in the terminal and overlay.
  devIndicators: false,
  // Next 16's CLI runner expects the TypeScript 7 executable layout. This
  // project intentionally stays on TypeScript 5.9, so use Next's compiler-API
  // checker for production builds; `npx tsc --noEmit` remains the explicit
  // standalone type-check command.
  experimental: {
    useTypeScriptCli: false,
  },
};

export default nextConfig;
