import colorsys
import math
import re
from playwright.async_api import Page
from stages.stage1_scraper.models import ColorData, ColorEntry, ContrastPair


def _rgb_str_to_tuple(rgb: str) -> tuple[int, int, int] | None:
    """Parse 'rgb(r, g, b)' or 'rgba(r, g, b, a)' to (r, g, b)."""
    m = re.match(r"rgba?\((\d+),\s*(\d+),\s*(\d+)", rgb)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3))
    return None


def _hex_to_tuple(hex_color: str) -> tuple[int, int, int] | None:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        return None
    try:
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except ValueError:
        return None


def _rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{r:02x}{g:02x}{b:02x}".upper()


def _relative_luminance(r: int, g: int, b: int) -> float:
    def linearize(c: int) -> float:
        v = c / 255
        return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)


def _contrast_ratio(fg: tuple, bg: tuple) -> float:
    l1 = _relative_luminance(*fg)
    l2 = _relative_luminance(*bg)
    lighter, darker = max(l1, l2), min(l1, l2)
    return round((lighter + 0.05) / (darker + 0.05), 2)


def _color_name(r: int, g: int, b: int) -> str:
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    if v < 0.15:
        return "Schwarz"
    if v > 0.9 and s < 0.1:
        return "Weiß"
    if s < 0.15:
        return f"Grau (L{int(v*100)})"
    hue_names = [
        (15, "Rot"), (45, "Orange"), (70, "Gelb"), (150, "Grün"),
        (200, "Türkis"), (260, "Blau"), (290, "Violett"), (330, "Pink"), (360, "Rot"),
    ]
    hue_deg = h * 360
    for threshold, name in hue_names:
        if hue_deg <= threshold:
            return name
    return "Rot"


def _are_similar(a: tuple, b: tuple, threshold: float = 30.0) -> bool:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b))) < threshold


async def extract_colors(page: Page) -> ColorData:
    raw = await page.evaluate("""
    () => {
        const colors = new Map();

        const addColor = (val, usage) => {
            if (!val) return;
            val = val.trim();
            if (val === 'transparent' || val === 'inherit' || val === 'initial' || val.startsWith('var(')) return;
            const key = val;
            if (!colors.has(key)) colors.set(key, { val, usages: new Set() });
            colors.get(key).usages.add(usage);
        };

        // CSS custom properties
        const cssVars = {};
        try {
            for (const sheet of document.styleSheets) {
                try {
                    for (const rule of sheet.cssRules) {
                        if (rule instanceof CSSStyleRule || rule instanceof CSSKeyframeRule) continue;
                        if (rule.style) {
                            for (let i = 0; i < rule.style.length; i++) {
                                const prop = rule.style[i];
                                if (prop.startsWith('--')) {
                                    const val = rule.style.getPropertyValue(prop).trim();
                                    if (val.startsWith('#') || val.startsWith('rgb')) {
                                        cssVars[prop] = val;
                                    }
                                }
                            }
                        }
                    }
                } catch(e) {}
            }
        } catch(e) {}

        // Computed styles on visible elements
        const elements = [...document.querySelectorAll('body *')].slice(0, 300);
        for (const el of elements) {
            const s = getComputedStyle(el);
            const bg = s.backgroundColor;
            const fg = s.color;
            const border = s.borderColor;

            if (bg && bg !== 'rgba(0, 0, 0, 0)') {
                const tag = el.tagName.toLowerCase();
                addColor(bg, tag === 'body' ? 'background' : tag === 'header' || tag === 'nav' ? 'navigation' : 'background');
            }
            if (fg) addColor(fg, 'text');
            if (border && border !== 'rgba(0, 0, 0, 0)') addColor(border, 'border');
        }

        // Contrast pairs from nav/header and main content
        const contrastPairs = [];
        const mainEl = document.querySelector('main, [role=main], article, .content') || document.body;
        const mainBg = getComputedStyle(mainEl).backgroundColor;
        const mainFg = getComputedStyle(mainEl).color;
        if (mainBg && mainFg) contrastPairs.push({ fg: mainFg, bg: mainBg });

        const navEl = document.querySelector('nav, header');
        if (navEl) {
            const navBg = getComputedStyle(navEl).backgroundColor;
            const navFg = getComputedStyle(navEl).color;
            if (navBg && navFg) contrastPairs.push({ fg: navFg, bg: navBg });
        }

        const btns = [...document.querySelectorAll('button, a.btn, a.button, [class*="btn"], [class*="button"]')].slice(0, 3);
        for (const btn of btns) {
            const s = getComputedStyle(btn);
            contrastPairs.push({ fg: s.color, bg: s.backgroundColor });
        }

        return {
            colors: [...colors.entries()].map(([k, v]) => ({ val: v.val, usages: [...v.usages] })),
            css_vars: cssVars,
            contrast_pairs: contrastPairs,
        };
    }
    """)

    palette: list[ColorEntry] = []
    seen_tuples: list[tuple] = []

    for item in raw.get("colors", []):
        val = item["val"]
        rgb_tuple = None

        if val.startswith("#"):
            rgb_tuple = _hex_to_tuple(val)
        elif val.startswith("rgb"):
            rgb_tuple = _rgb_str_to_tuple(val)

        if rgb_tuple is None:
            continue

        if any(_are_similar(rgb_tuple, s) for s in seen_tuples):
            continue
        seen_tuples.append(rgb_tuple)

        hex_val = _rgb_to_hex(*rgb_tuple)
        usage = ", ".join(item.get("usages", []))
        palette.append(ColorEntry(
            hex=hex_val,
            rgb=f"rgb{rgb_tuple}",
            usage=usage,
            name=_color_name(*rgb_tuple),
        ))

    # Limit palette to 12 most significant colors
    palette = palette[:12]

    contrast_pairs: list[ContrastPair] = []
    seen_pairs: set[tuple] = set()
    for pair in raw.get("contrast_pairs", []):
        fg_tuple = _rgb_str_to_tuple(pair.get("fg", "")) if pair.get("fg", "").startswith("rgb") else _hex_to_tuple(pair.get("fg", ""))
        bg_tuple = _rgb_str_to_tuple(pair.get("bg", "")) if pair.get("bg", "").startswith("rgb") else _hex_to_tuple(pair.get("bg", ""))

        if fg_tuple is None or bg_tuple is None:
            continue
        if bg_tuple == (0, 0, 0, 0) if len(bg_tuple) == 4 else bg_tuple == (0, 0, 0):
            continue

        key = (fg_tuple, bg_tuple)
        if key in seen_pairs:
            continue
        seen_pairs.add(key)

        ratio = _contrast_ratio(fg_tuple[:3], bg_tuple[:3])
        fg_hex = _rgb_to_hex(*fg_tuple[:3])
        bg_hex = _rgb_to_hex(*bg_tuple[:3])

        contrast_pairs.append(ContrastPair(
            fg=fg_hex,
            bg=bg_hex,
            ratio=ratio,
            passes_aa=ratio >= 4.5,
            passes_aa_large=ratio >= 3.0,
        ))

    return ColorData(
        palette=palette,
        contrast_pairs=contrast_pairs[:10],
        css_vars=raw.get("css_vars", {}),
    )
