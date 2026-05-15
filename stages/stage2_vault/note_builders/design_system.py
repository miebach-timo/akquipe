"""Vault note: DESIGN.md — full SkillUI-style design system documentation for Claude context."""
from stages.stage1_scraper.models import ScrapedData


def build_design_system(data: ScrapedData) -> str:
    colors = data.colors.palette
    fonts = data.typography.families
    spacing = data.spacing_tokens
    motion = data.motion_tokens
    comp = data.components
    assets = data.raw_assets

    # Color table
    color_rows = "\n".join(
        f"| {c.hex} | {c.usage} |"
        for c in colors[:8]
    ) or "| — | — |"

    # Typography
    font_rows = ""
    if fonts:
        font_rows += f"| Body | {fonts[0]} | {data.typography.body_size or '16px'} | — | {data.typography.line_height or '1.6'} |\n"
        for f in fonts[1:3]:
            font_rows += f"| — | {f} | — | — | — |\n"
    else:
        font_rows = "| Body | sans-serif | 16px | — | 1.6 |\n"

    # Spacing
    pad_str = " / ".join(spacing.common_paddings[:6]) or "—"
    margin_str = " / ".join(spacing.common_margins[:6]) or "—"
    gap_str = " / ".join(spacing.common_gaps[:4]) or "—"
    radius_str = " / ".join(spacing.common_radii[:5]) or "—"
    shadow_str = "\n".join(f"- `{s}`" for s in spacing.common_shadows[:3]) or "— keine erkannt"

    # Motion
    transition_str = "\n".join(f"- `{t}`" for t in motion.transitions[:5]) or "— keine"
    anim_str = ", ".join(motion.animation_names[:5]) or "—"
    motion_lib_str = ", ".join(motion.animation_libraries) or "—"
    reduced_motion_str = "✓ unterstützt" if motion.has_reduced_motion_support else "✗ fehlt"

    # Components
    nav_sticky = " (sticky/fixed)" if comp.nav_is_sticky else ""
    nav_hamburger = " · Hamburger-Menu vorhanden" if comp.nav_has_hamburger else ""
    btn_texts = ", ".join(f'"{b.text}"' for b in comp.buttons[:5] if b.text) or "—"
    form_types = ", ".join(
        ", ".join(f.input_types) for f in comp.forms[:2]
    ) or "— kein Formular"

    # Tech stack
    fw_str = ", ".join(assets.frameworks_detected) or "Vanilla JS / unbekannt"
    cdn_str = ", ".join(assets.cdns_detected) or "—"
    font_cdn = "Google Fonts" if assets.external_stylesheets and any("googleapis" in s for s in assets.external_stylesheets) else "—"

    return f"""---
title: Design System
type: design-system
domain: {data.domain}
tags: [design-system, akquipe, brand-tokens]
---

# Design System — {data.domain}

Automatisch extrahiert von akquipe. Wird als Kontext für Stage 3 (Imitat) und Stage 5 (Redesign) verwendet.

---

## Color Tokens

| Hex | Verwendung |
|---|---|
{color_rows}

**CSS-Variablen aus der Seite:**
{chr(10).join(f'- `{k}: {v}`' for k, v in list(data.colors.css_vars.items())[:8]) or "— keine CSS-Variablen erkannt"}

---

## Typography Scale

| Ebene | Font | Größe | Gewicht | Line-Height |
|---|---|---|---|---|
{font_rows}
**Google Fonts:** {font_cdn}

---

## Spacing Scale

**Padding (häufigste):** {pad_str}
**Margin (häufigste):** {margin_str}
**Gap (häufigste):** {gap_str}

---

## Border Radius

{radius_str}

---

## Shadows

{shadow_str}

---

## Component Inventory

### Navigation
- **Typ:** {comp.nav_type}{nav_sticky}{nav_hamburger}
- **Button-Anzahl gesamt:** {comp.button_count}
- **Haupt-CTAs:** {btn_texts}

### Formulare
- **Anzahl:** {comp.form_count}
- **Input-Typen:** {form_types}

### Seitenstruktur
- **Hero-Section:** {"✓" if comp.has_hero else "✗"}
- **Cards:** {"✓" if comp.has_cards else "✗"}
- **Modal/Overlay:** {"✓" if comp.has_modal else "✗"}

---

## Motion & Animations

**Transitions:**
{transition_str}

**Animation-Namen:** {anim_str}
**Bibliotheken:** {motion_lib_str}
**prefers-reduced-motion:** {reduced_motion_str}

---

## Framework & Tech Stack

- **JS-Framework:** {fw_str}
- **CDNs erkannt:** {cdn_str}
- **Font-CDN:** {font_cdn}
- **Externe Stylesheets:** {len(assets.external_stylesheets)}
- **Externe Scripts:** {len(assets.external_scripts)}
"""
