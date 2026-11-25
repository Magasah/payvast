# Payvast design system

Who it is for: Tajik workers in Russia, mostly on mid-range Android phones and mobile data.
The job of every screen: get a person from "I paid" to "I am connected" without help.

## Idea

**The pass.** A subscription is shown as a lapis-blue pass with an atlas-silk (ikat) edge,
like a travel card. Lapis comes from Badakhshan, atlas is the silk every family knows.
The pass is the one bold element. Everything around it stays quiet: flat white panels,
plain lists, no gradients, no decorative shadows.

## Tokens

Defined as CSS variables in `src/app/globals.css`, mapped to Tailwind in `tailwind.config.ts`.
Use the Tailwind names, never raw hex in components.

| Token            | Hex       | Use                                              |
|------------------|-----------|--------------------------------------------------|
| `paper`          | `#F2F4F8` | page background                                  |
| `surface`        | `#FFFFFF` | panels, inputs                                   |
| `ink`            | `#16203D` | text                                             |
| `ink-soft`       | `#4A5577` | secondary text                                   |
| `line`           | `#D9DEEA` | borders, dividers                                |
| `lapis`          | `#24439C` | primary actions, links, numerals                 |
| `lapis-deep`     | `#172E6E` | the pass, hover of primary                       |
| `pomegranate`    | `#C7354C` | errors, rejected, ikat                           |
| `saffron`        | `#D98E1F` | waiting for the user (receipt), ikat             |
| `pistachio`      | `#2F7D4F` | active, confirmed                                |

Every color except ink/line has a `-tint` for backgrounds of badges and notices.

**Status colors are fixed** (`src/lib/status.ts`): saffron = user must act, lapis = we are
checking, pistachio = done, pomegranate = rejected.

## Type

- **Commissioner Flair** (display): Commissioner with the flair axis at 100, weights 600–900.
  Headings, prices, numerals. Tight tracking (`tracking-display`).
- **Golos Text** (text): body and UI, weights 400–700.

Both are self-hosted from `public/fonts` (built by `scripts/build_fonts.py`), split by
unicode-range so a page downloads only the scripts it shows. Both cover the Tajik letters
ӣ ҳ ҷ қ ӯ ғ; do not switch to a font without checking them.

Scale (1.25): `xs 13`, `sm 15`, `base 16`, `lg 20`, `xl 25`, `2xl 31`, `3xl 39`, `4xl 49`, `5xl 61`.
Sentence case everywhere. No all-caps labels, no eyebrow text above headings.

## Shape

Radius encodes hierarchy: `sm 6` badges, `md 12` controls, `lg 20` panels, `pass 28` the pass only.
Panels have a 1px `line` border and no shadow. Only the pass has a shadow.

## Components (`src/components/ui`)

- `Button` / `ButtonLink`: tones `primary`, `quiet`, `success`, `danger`, `inverse` (on the pass);
  sizes `sm 36px`, `md 44px`, `lg 56px`. One primary button per screen.
- `Field`: label above, hint or error below, 48px tall input (thumb-sized).
- `Badge`: status with a dot. Pick the tone from `lib/status.ts`.
- `Notice`: inline message with a colored left rule. Errors say what happened and what to do.
- `Panel`: flat white surface.
- `Ikat`: the silk band, inline SVG. Used only on the pass.
- `Pass` (`src/components/Pass.tsx`) and `TariffRow` (`src/components/TariffRow.tsx`).

## Layout

- Mobile first. Page width `max-w-page` (68rem), side gutter 16px on phones, 24px from `sm`.
- Text is left aligned. Reading width `max-w-prose` (38rem).
- Tariffs are rows of one price list (duration first, then price, then per-month), not cards.
- Numbered markers only for real sequences (the 3 steps, setup instructions).

## Motion

One orchestrated moment: the pass's silk edge unrolls once on the home page.
Otherwise motion only answers an action (button press, tab change).
`prefers-reduced-motion` turns all of it off.

## Performance budget

- Public pages (home, instructions) are server components with no page-specific JS.
- Only the message namespaces that client components use are sent to the browser.
- Fonts ≤ 160 KB total, preloaded for the Cyrillic text face and display face.
- No icon fonts, no image files for decoration, no UI libraries.

## Copy

Plain verbs, the same word for the same action through a flow
("Ба пардохт гузаштан" → payment panel → "Тасдиқ шуд").
Describe the product as защищённое подключение / пайвасти ҳифзшуда. Never mention bypassing blocks.
