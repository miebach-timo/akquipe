from stages.stage1_scraper.models import ScrapedData


def build_typography(data: ScrapedData) -> str:
    font_rows = "\n".join(f"| {f} | — |" for f in data.typography.families)
    gf_list = "\n".join(f"- {url}" for url in data.typography.google_fonts) or "keine"

    return f"""---
title: Typography
type: client-audit-section
domain: {data.domain}
---

# Typografie — {data.domain}

[[_Overview]] · [[Colors]] · [[Icons]]

---

## Schriftfamilien

| Familie | Quelle |
|---|---|
{font_rows}

**Body-Schriftgröße:** {data.typography.body_size or "nicht ermittelt"}
**Zeilenhöhe:** {data.typography.line_height or "nicht ermittelt"}
**Schriftgewichte:** {", ".join(data.typography.weights) or "nicht ermittelt"}

---

## Google Fonts Links

{gf_list}

---

## WCAG-Hinweise

> Mindest-Schriftgröße für normalen Text: **16px** (12pt)
> Mindest-Schriftgröße für "großen Text" (reduzierte Kontrast-Anforderung): **18px** normal / **14px** fett

- Body: {data.typography.body_size or "unbekannt"} {"✅ OK" if data.typography.body_size and "16" in data.typography.body_size else "⚠ prüfen"}
"""
