import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

// Rewrites are resolved at build time for the standalone output,
// so API_INTERNAL_URL must be available during `next build`.
const apiUrl = process.env.API_INTERNAL_URL ?? "http://localhost:8000";

const isDev = process.env.NODE_ENV !== "production";

// Next.js 14 hydrates with inline scripts, so script-src needs 'unsafe-inline' (no nonces:
// they would force every page to render dynamically). XSS is blocked at the source instead:
// React escapes all text and the code never uses dangerouslySetInnerHTML.
const csp = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline'${isDev ? " 'unsafe-eval'" : ""}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob:",
  "font-src 'self'",
  "connect-src 'self'",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  // The site opens as a Telegram Mini App; Telegram Web shows it in an iframe.
  "frame-ancestors 'self' https://web.telegram.org https://*.telegram.org",
].join("; ");

const securityHeaders = [
  { key: "Content-Security-Policy", value: csp },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "no-referrer" },
  { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains" },
  { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
  {
    key: "Permissions-Policy",
    value: "camera=(), microphone=(), geolocation=(), payment=(), usb=()",
  },
];

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  poweredByHeader: false,
  reactStrictMode: true,
  async rewrites() {
    // Same-origin proxy: the browser talks only to the web origin,
    // so the SameSite=Strict refresh cookie is always sent.
    // /api/internal/* (bot-only endpoints) is never proxied: browsers get Next's 404.
    return [
      { source: "/api/:path((?!internal(?:/|$)).*)", destination: `${apiUrl}/api/:path` },
    ];
  },
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
};

export default withNextIntl(nextConfig);
