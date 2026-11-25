import { useId } from "react";

import { cx } from "./cx";

/**
 * Atlas (ikat) silk band, the brand's single decorative element.
 * Stepped diamonds with feathered edges, the way dyed warp threads blur in real atlas.
 * Vertical band. Pure inline SVG: no image request, ~1 KB.
 */
export function Ikat({ className }: { className?: string }) {
  const id = useId().replace(/:/g, "");
  // The viewBox is one motif wide: the band scales the motif to its own width
  // and crops the length, so the pattern never gets cut in half.
  return (
    <svg
      aria-hidden
      className={cx("block", className)}
      viewBox="0 0 48 1280"
      preserveAspectRatio="xMidYMin slice"
      width="100%"
      height="100%"
    >
      <defs>
        <pattern
          id={`ikat-${id}`}
          width="48"
          height="64"
          patternUnits="userSpaceOnUse"
        >
          <rect width="48" height="64" fill="rgb(var(--c-lapis-deep))" />
          {/* outer stepped diamond, pomegranate */}
          <path
            d="M24 0h4v6h4v6h4v8h4v12h-4v8h-4v6h-4v6h-4v12h-4v-6h-4v-6h-4v-8H8V32h4v-8h4v-6h4V6h4z"
            fill="rgb(var(--c-pomegranate))"
          />
          {/* inner diamond, saffron */}
          <path d="M22 14h4v6h4v8h4v8h-4v8h-4v6h-4v-6h-4v-8h-4v-8h4v-8h4z" fill="rgb(var(--c-saffron))" />
          {/* core, white */}
          <path d="M22 26h4v4h2v4h-2v4h-4v-4h-2v-4h2z" fill="#fff" />
          {/* feathered warp edges */}
          <path
            d="M0 0h3v14H0zM45 0h3v10h-3zM0 40h2v14H0zM46 44h2v20h-2zM4 60h2v4H4zM42 0h2v5h-2z"
            fill="rgb(var(--c-lapis))"
          />
        </pattern>
      </defs>
      <rect width="100%" height="100%" fill={`url(#ikat-${id})`} />
    </svg>
  );
}
