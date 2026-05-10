from stages.stage1_scraper.models import ScrapedData


def build_colors(data: ScrapedData) -> str:
    palette_rows = "\n".join(
        f"| `{c.hex}` | {c.name} | {c.usage} | {c.rgb} |"
        for c in data.colors.palette
    )

    contrast_rows = "\n".join(
        f"| `{p.fg}` | `{p.bg}` | {p.ratio}:1 | {'✅ PASS' if p.passes_aa else '❌ FAIL'} | {'✅' if p.passes_aa_large else '❌'} |"
        for p in data.colors.contrast_pairs
    )

    css_vars_block = ""
    if data.colors.css_vars:
        vars_list = "\n".join(f"  {k}: {v};" for k, v in list(data.colors.css_vars.items())[:20])
        css_vars_block = f"""
## CSS Custom Properties

```css
:root {{
{vars_list}
}}
```
"""

    return f"""---
title: Colors
type: client-audit-section
domain: {data.domain}
---

# Farben — {data.domain}

[[_Overview]] · [[Typography]] · [[Icons]]

---

## Farbpalette

| Hex | Name | Verwendung | RGB |
|---|---|---|---|
{palette_rows}

---

## Farbkontrast-Analyse (WCAG 2.1)

> Mindest-Kontrastverhältnis: **4.5:1** (AA Text) / **3:1** (AA Large/UI)

| Vordergrund | Hintergrund | Verhältnis | AA Text | AA Large |
|---|---|---|---|---|
{contrast_rows}
{css_vars_block}
"""
