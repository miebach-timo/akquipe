# akquipe — Claude Code Kontext

## Was ist akquipe?

UX/UI Freelancer Pipeline: Automatisch Kunden-Websites scrapen → analysieren → auditieren → als modernes Next.js-Projekt nachbauen → als Angebotspaket versenden.

## Verzeichnisstruktur

```
pipeline.py          # CLI-Einstieg (Typer)
config/settings.py   # Alle Einstellungen via .env
shared/run_state.py  # RunState JSON — Verbindungsglied zwischen Stages
stages/
  stage1_scraper/    # Playwright-Scraper (Farben, Fonts, Icons, Sitemap, Screenshots)
  stage2_vault/      # Obsidian Vault Writer (Markdown Notes)
  stage3_audit/      # Claude Audit-Agent mit tool_use Loop
  stage4_reconstruct/# Next.js + Tailwind Rekonstruktion
  stage5_package/    # ZIP-Bundle + Preismodell
output/              # Alle Run-Artefakte (gitignored)
```

## Wichtige Konventionen

- **RunState** (`shared/run_state.py`): Jede Stage liest aus und schreibt in `output/<run_id>/run_state.json`. So ist jede Stage einzeln wiederholbar.
- **Pydantic überall**: Alle Datenstrukturen sind Pydantic-Modelle.
- **Kein direktes `print()`**: Immer `shared/logger.py` verwenden (Rich-basiert).
- **Async wo möglich**: Playwright-Code ist async; Stage-Orchestratoren nutzen `asyncio.run()`.

## CLI-Befehle

```bash
python pipeline.py run https://example.com          # Vollständige Pipeline
python pipeline.py run https://example.com --stages 1,2,3  # Nur bestimmte Stages
python pipeline.py run https://example.com --skip-reconstruct
python pipeline.py resume <run-id>                  # Abgebrochenen Run fortsetzen
python pipeline.py list-runs                         # Alle Runs auflisten
```

## Environment Setup

```bash
pip install -r requirements.txt
playwright install chromium
cp .env.example .env
# .env editieren: ANTHROPIC_API_KEY setzen
```

## RunState JSON Schema

```json
{
  "run_id": "example_com_20260510_143022",
  "url": "https://example.com",
  "domain": "example.com",
  "started_at": "2026-05-10T14:30:22",
  "scraper": { "status": "done", "data_path": "...", "pages_crawled": 12 },
  "vault": { "status": "done", "folder_path": "..." },
  "audit": { "status": "done", "scores": {...}, "pdf_path": "..." },
  "reconstruct": { "status": "done", "project_path": "..." },
  "package": { "status": "done", "zip_path": "..." }
}
```

## Audit-Kategorien

1. **Barrierefreiheit** (WCAG 2.1 AA): Kontrast, Alt-Texte, Semantik, Keyboard-Nav, ARIA
2. **SEO**: Meta-Tags, Heading-Hierarchie, Schema.org, Crawlability
3. **UX/UI**: Visuelle Hierarchie, CTA-Klarheit, Mobile Responsiveness, Design-Modernität
