from shared.run_state import RunState


def calculate_price(state: RunState, day_rate: float) -> float:
    """Heuristic pricing based on audit findings and pages crawled."""
    hours = 0.0

    # Base: Analysis & Audit delivery (always included)
    hours += 2.0  # Report preparation and presentation

    # Pages crawled = complexity indicator
    pages = state.scraper.pages_crawled
    hours += min(pages * 0.25, 4.0)  # max 4h for site analysis

    # Findings = implementation effort
    total_findings = sum(state.audit.findings_count.values())
    critical = sum(1 for cat_count in [state.audit.scores] if cat_count.get("accessibility", 100) < 50)
    hours += total_findings * 0.5  # ~30min per finding to fix
    hours += critical * 2.0  # critical issues get extra weight

    # Reconstruction included?
    if state.reconstruct.status.value == "done":
        hours += 8.0  # Base: Next.js project setup + components
        hours += min(pages * 0.5, 6.0)  # Additional pages

    # Cap at reasonable freelance project size
    hours = min(hours, 40.0)

    price = (hours / 8.0) * day_rate
    return round(price, -1)  # Round to nearest 10 EUR


def format_pricing_md(state: RunState, price: float, day_rate: float) -> str:
    from datetime import date

    findings_total = sum(state.audit.findings_count.values())
    has_reconstruct = state.reconstruct.status.value == "done"

    return f"""# Preisvorschlag — {state.domain}

**Erstellt:** {date.today().strftime("%d.%m.%Y")}
**Tagessatz:** {day_rate:,.0f} EUR

---

## Leistungsumfang

| Leistung | Inbegriffen |
|---|---|
| Website-Analyse & Scraping | ✅ |
| Barrierefreiheits-Audit (WCAG 2.1 AA) | ✅ |
| SEO-Analyse | ✅ |
| UX/UI-Bewertung | ✅ |
| Schriftlicher Audit-Report (PDF) | ✅ |
| Modernisierter Website-Prototyp (Next.js) | {"✅" if has_reconstruct else "—"} |
| Präsentation der Ergebnisse (30 min Online) | ✅ |

---

## Kalkulationsgrundlage

- Seiten analysiert: {state.scraper.pages_crawled}
- Befunde gesamt: {findings_total}
- Audit-Scores: Accessibility {state.audit.scores.get("accessibility", "—")}/100 · SEO {state.audit.scores.get("seo", "—")}/100 · UX/UI {state.audit.scores.get("ux_ui", "—")}/100

---

## Gesamtpreis

> **{price:,.0f} EUR** (netto, zzgl. MwSt.)

---

*Angebot gültig 30 Tage. Bei Beauftragung wird der Betrag auf eine mögliche Implementierung angerechnet.*
"""
