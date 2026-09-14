import type { NextConfig } from "next";

// No GitHub Pages o site fica em https://<usuario>.github.io/<repo>/; NEXT_PUBLIC_BASE_PATH="/<repo>" no build.
// Localmente (sem a variável) o site é servido na raiz.
const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

const nextConfig: NextConfig = {
  output: "export",
  trailingSlash: true,
  basePath,
  assetPrefix: basePath || undefined,
  images: { unoptimized: true },
};

export default nextConfig;
