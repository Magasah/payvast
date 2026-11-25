"""Build the self-hosted font files in public/fonts.

Run from apps/web after `npm install`:
    uv run --with fonttools --with brotli python scripts/build_fonts.py

Fontsource ships every axis of a variable font. We pin the axes we do not use and
narrow the weight range, which makes each file several times smaller. Files stay split
by script (latin / cyrillic / cyrillic-ext) so the browser downloads only what a page needs
via unicode-range; cyrillic-ext carries the Tajik letters ӣ ҳ ҷ қ ӯ ғ.
"""

from pathlib import Path

from fontTools import subset as ftsubset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

ROOT = Path(__file__).resolve().parents[1]
NM = ROOT / "node_modules" / "@fontsource-variable"
OUT = ROOT / "public" / "fonts"

FAMILIES = {
    # Display: flared terminals at full flair, heavy weights only.
    "commissioner": ("full", {"wght": (600, 900), "FLAR": 100, "VOLM": 100, "slnt": 0}),
    # Text and UI.
    "golos-text": ("wght", {"wght": (400, 700)}),
}
SUBSETS = ["latin", "cyrillic", "cyrillic-ext"]
# The Latin file only needs ASCII, Latin-1 punctuation and general punctuation:
# the UI text is Cyrillic, Latin is used for "Payvast", emails, URLs and digits.
LATIN_KEEP = [*range(0x20, 0x7F), *range(0xA0, 0x100), *range(0x2010, 0x2027), 0x20AC, 0x2116]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for family, (axes, limits) in FAMILIES.items():
        for subset in SUBSETS:
            src = NM / family / "files" / f"{family}-{subset}-{axes}-normal.woff2"
            font = instancer.instantiateVariableFont(TTFont(src), limits)
            if subset == "latin" and family == "commissioner":  # golos latin is already small
                opts = ftsubset.Options()
                opts.layout_features = ["*"]
                opts.name_IDs = ["*"]
                sub = ftsubset.Subsetter(opts)
                sub.populate(unicodes=LATIN_KEEP)
                sub.subset(font)
            font.flavor = "woff2"
            out = OUT / f"{family}-{subset}.woff2"
            font.save(out)
            print(f"{out.name}: {src.stat().st_size // 1024} KB -> {out.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
