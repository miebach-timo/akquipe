from stages.stage1_scraper.models import ScrapedData


def build_icons(data: ScrapedData) -> str:
    lib_list = "\n".join(f"- {lib}" for lib in data.icons.libraries) or "- keine erkannt"
    svg_list = "\n".join(f"- ![[assets/icons/{f.split('/')[-1]}]]" for f in data.icons.svg_files[:10]) or "keine"

    return f"""---
title: Icons
type: client-audit-section
domain: {data.domain}
---

# Icons — {data.domain}

[[_Overview]] · [[Colors]] · [[Typography]]

---

## Erkannte Icon-Bibliotheken

{lib_list}

---

## Custom SVGs

**Anzahl SVG-Elemente auf Startseite:** {data.icons.svg_count}

{svg_list}

---

## Hinweise

> Alle Icons sollten `aria-hidden="true"` haben (dekorativ) ODER ein `aria-label` (semantisch).
> Icon-only Buttons brauchen zwingend einen zugänglichen Namen (aria-label oder sr-only Text).
"""
