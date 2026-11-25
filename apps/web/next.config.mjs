import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

// Rewrites are resolved at build time for the standalone output,
// so API_INTERNAL_URL must be available during `next build`.
const apiUrl = process.env.API_INTERNAL_URL ?? "http://localhost:8000";

const securityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "no-referrer" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
];

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  poweredByHeader: false,
  reactStrictMode: true,
  async rewrites() {
    // Same-origin proxy: the browser talks only to the web origin,
    // so the SameSite=Strict refresh cookie is always sent.
    return [{ source: "/api/:path*", destination: `${apiUrl}/api/:path*` }];
  },
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
};

export default withNextIntl(nextConfig);
