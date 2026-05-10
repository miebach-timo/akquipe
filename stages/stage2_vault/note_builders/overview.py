from datetime import date
from stages.stage1_scraper.models import ScrapedData


def build_overview(data: ScrapedData, run_id: str) -> str:
    primary_colors = [c.hex for c in data.colors.palette[:5]]
    primary_font = data.typography.families[0] if data.typography.families else "unbekannt"
    icon_libs = ", ".join(data.icons.libraries) if data.icons.libraries else "keine erkannt"

    frontmatter = f"""---
title: "{data.domain}"
type: client-audit
domain: {data.domain}
url: {data.url}
scraped_date: {date.today().isoformat()}
pipeline_run_id: {run_id}
status: scraped
audit_score_accessibility: null
audit_score_seo: null
audit_score_ux_ui: null
pages_crawled: {data.pages_crawled}
primary_colors: {primary_colors}
primary_font: "{primary_font}"
icon_libraries: {data.icons.libraries}
tags: [client, akquipe, audit-pending]
---"""

    h1 = data.content.h1_texts[0] if data.content.h1_texts else data.domain
    cta_list = "\n".join(f'- "{c.text}" → {c.href}' for c in data.content.ctas[:5])
    color_rows = "\n".join(
        f"| {c.hex} | {c.name} | {c.usage} |"
        for c in data.colors.palette[:8]
    )

    body = f"""
# {data.domain}

**URL:** {data.url}
**Gescrapt:** {date.today().isoformat()}
**Seiten gecrawlt:** {data.pages_crawled}

---

## Navigation
→ [[Colors]] · [[Typography]] · [[Icons]] · [[Page-Hierarchy]] · [[User-Flow]] · [[Screenshots]] · [[Audit-Report]]

---

## Zusammenfassung

**Seitentitel:** {data.meta.title or "FEHLT"}
**H1:** {h1}
**Wortanzahl (Startseite):** {data.content.word_count}

### Top CTAs
{cta_list or "keine erkannt"}

---

## Schnell-Übersicht Farben

| Hex | Name | Verwendung |
|---|---|---|
{color_rows}

---

## Technische Punkte

| Merkmal | Wert |
|---|---|
| Viewport Meta | {data.meta.viewport or "FEHLT ⚠"} |
| Meta Description | {"✓" if data.meta.description else "FEHLT ⚠"} |
| Bilder ohne Alt | {data.content.images_missing_alt} von {data.content.images_total} |
| H1-Tags | {data.content.h1_count} (erwartet: 1) |
| Impressum | {"✓" if data.content.has_impressum else "✗"} |
| Datenschutz | {"✓" if data.content.has_privacy else "✗"} |
| HTTPS | {"✓" if data.url.startswith("https") else "✗"} |
| Schriften | {", ".join(data.typography.families[:3])} |
| Icon-Bibliotheken | {icon_libs} |
"""
    return frontmatter + body
