from shared.run_state import RunState


def calculate_price(state: RunState, day_rate: float) -> float:
    hours = 2.0  # Base: analysis & report delivery

    pages = state.scraper.pages_crawled
    hours += min(pages * 0.25, 4.0)

    total_findings = sum(state.audit.findings_count.values())
    critical_score = state.audit.scores.get("accessibility", 100)
    hours += total_findings * 0.5
    if critical_score < 50:
        hours += 2.0

    # Imitate stage included
    if state.imitate.status.value == "done":
        hours += 6.0
        hours += min(pages * 0.3, 4.0)

    # Redesign iterations
    iteration_count = len(state.redesign.iterations)
    hours += iteration_count * 0.5

    # Cap
    hours = min(hours, 40.0)
    price = (hours / 8.0) * day_rate
    return round(price, -1)


def format_pricing_md(state: RunState, price: float, day_rate: float) -> str:
    from datetime import date

    findings_total = sum(state.audit.findings_count.values())
    has_imitate = state.imitate.status.value == "done"
    has_redesign = state.redesign.status.value == "done"
    iterations = len(state.redesign.iterations)

    scores = state.audit.scores
    score_str = (
        f"Accessibility {scores.get('accessibility', '—')}/100 · "
        f"SEO {scores.get('seo', '—')}/100 · "
        f"UX/UI {scores.get('ux_ui', '—')}/100 · "
        f"Usability {scores.get('usability', '—')}/100"
    )

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
| Usability & Responsiveness-Check | ✅ |
| Schriftlicher Audit-Report (PDF) | ✅ |
| 1:1 Website-Imitat (Next.js) | {"✅" if has_imitate else "—"} |
| Modernisierter Website-Prototyp | {"✅" if has_redesign else "—"} |
| Design-Iterationen | {"✅ " + str(iterations) + "x" if iterations > 0 else "—"} |
| Präsentation der Ergebnisse (30 min Online) | ✅ |

---

## Kalkulationsgrundlage

- Seiten analysiert: {state.scraper.pages_crawled}
- Befunde gesamt: {findings_total}
- Audit-Scores: {score_str}

---

## Gesamtpreis

> **{price:,.0f} EUR** (netto, zzgl. MwSt.)

---

*Angebot gültig 30 Tage. Bei Beauftragung wird der Betrag auf die Implementierung angerechnet.*
"""
