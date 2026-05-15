# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Was ist akquipe?

UX/UI Freelancer Akquise-Pipeline v2: Automatisch Kunden-Websites scrapen → Design dokumentieren → Website imitieren → auditieren → iterativ redesignen → als Angebotspaket versenden.

## Entwicklungs-Befehle

```bash
# Pipeline starten (alle 6 Stages)
python pipeline.py run https://example.com
python pipeline.py run https://example.com --stages 1,2,3
python pipeline.py resume <run-id> --stages 4,5,6

# Audit freigeben (manueller Review-Checkpoint nach Stage 4)
python pipeline.py approve <run-id>
python pipeline.py approve <run-id> --notes "Kontrast-Problem bei Nav wichtig"

# Neue Redesign-Iteration starten
python pipeline.py redesign <run-id> --feedback "Mehr Kontrast" --variance 7 --motion 4

# Runs anzeigen
python pipeline.py list-runs

# Streamlit Dashboard
streamlit run app.py

# Setup (einmalig)
pip install -r requirements.txt
playwright install chromium
cp .env.example .env  # ANTHROPIC_API_KEY setzen
```

## Architektur v2

### Pipeline-Flow (6 Stages)

Jede Stage liest ihren Input aus `RunState` und schreibt ihren Output zurück.

```
pipeline.py (Typer CLI)
  └─ asyncio.run(_execute_pipeline())
       ├─ Stage 1: run_scraper()       → async, Playwright + 4 neue Extraktoren
       ├─ Stage 2: run_vault_writer()  → sync, + DESIGN.md
       ├─ Stage 3: run_imitate()       → async, 1:1 Next.js Replica
       ├─ Stage 4: run_audit()         → async, 4 Kategorien + Manual Review Checkpoint
       ├─ Stage 5: run_redesign()      → async, iterativ mit Taste-Dials
       └─ Stage 6: run_packager()      → sync, ZIP + Changelog
```

**Wichtig:** Nach Stage 4 pausiert die Pipeline bis der User den Audit freigibt (`manual_review_approved = True`). Stage 5+6 laufen nur danach.

### Stage-Verzeichnisse

```
stages/stage1_scraper/       — Playwright-Scraper + 7 Extraktoren
stages/stage2_vault/         — Obsidian-Notes inkl. DESIGN.md
stages/stage3_imitate/       — 1:1 Next.js Imitat (treu zur Original-Website)
stages/stage4_audit/         — Audit mit 4 Kategorien + Impeccable-Regeln
stages/stage5_redesign/      — Iteratives Redesign mit UI/UX Pro Max + Taste-Dials
stages/stage6_package/       — ZIP-Paket mit Changelog + Anschreiben
```

**Legacy:** `stages/stage3_audit/` und `stages/stage4_reconstruct/` und `stages/stage5_package/` — für alte Runs (pre-v2) beibehalten.

### Neue Extraktoren (Stage 1)

Alle in `stages/stage1_scraper/extractors/`:
- `raw_assets.py` — HTML-Dump, inline CSS/JS, Framework-Detection (React/Vue/Next.js/etc.)
- `spacing.py` — Padding/Margin/Gap/Border-Radius/Box-Shadow aus computed styles
- `motion.py` — CSS Transitions/Animations, prefers-reduced-motion, Animation-Libraries
- `components.py` — Buttons, Forms, Nav-Typ, Cards, Hero, Modal Inventar

### DESIGN.md (Stage 2)

`stages/stage2_vault/note_builders/design_system.py` erstellt `DESIGN.md` im Vault:
- Color Tokens + CSS-Variablen
- Typography Scale
- Spacing Scale (häufigste Werte)
- Border Radius + Shadows
- Component Inventory
- Motion & Animations
- Framework & Tech Stack

Diese Datei wird von Stage 3 (Imitat) und Stage 5 (Redesign) als Design-Kontext für Claude verwendet.

### Manual Review Checkpoint (Stage 4)

`AuditState` hat neue Felder: `manual_review_approved`, `manual_review_notes`, `manual_review_approved_at`.

Freigabe entweder:
- Im Dashboard (Tab "Audit" → "Audit freigeben" Button)
- Per CLI: `python pipeline.py approve <run-id>`

### Taste-Dials (Stage 5)

`RedesignParams` in `shared/run_state.py`:
- `design_variance` 1–10 (konservativ → experimentell)
- `motion_intensity` 1–10 (statisch → animiert)
- `visual_density` 1–10 (luftig → dicht)
- `style_direction` (auto | modern-corporate | minimal | bold | ...)

Jede Iteration wird in `RedesignState.iterations: list[RedesignIteration]` gespeichert.

### State-Management

`shared/run_state.py` — alle Pydantic-Modelle:
- `ScraperState`, `VaultState`
- `ImitateState` (NEU)
- `AuditState` + `manual_review_*` (erweitert)
- `RedesignParams`, `RedesignIteration`, `RedesignState` (NEU)
- `ReconstructState` (legacy, für alte Runs)
- `PackageState`

Status-Enum: `pending → running → done | failed | skipped`

### Zwei-Modell-Architektur

- **Stage 4 (Audit):** `claude-sonnet-4-6` — 4 Kategorien, 27 Impeccable-Anti-Pattern-Regeln, max. 12 Iterationen
- **Stage 3/5 (Imitat/Redesign):** `claude-haiku-4-5-20251001` — 4 React-Komponenten (Navigation, Hero, Features, Footer)

### Anthropic API im Pipeline-Kontext

**Bekanntes Problem:** `RemoteProtocolError: Server disconnected` bei async httpx aus Pipeline-Kontext (Corporate-Proxy / ProactorEventLoop-Konflikt mit Playwright).

**Lösung:** Synchroner `anthropic.Anthropic`-Client in `_run_sync()`, aufgerufen via `asyncio.to_thread()`. Gilt für Stage 3 (Imitat), Stage 4 (Audit), Stage 5 (Redesign).

### Streamlit Dashboard (`app.py`)

6 Tabs pro Projekt:
- **Übersicht**: 6-Stage Status, 4 Audit-Scores, Farbpalette, Screenshots (Desktop/Mobile/Tablet)
- **Akquise**: Status-Tracking → `output/<run-id>/client_meta.json`
- **Imitat**: 1:1-Replica Infos, Original vs. Imitat Vergleich, DESIGN.md Preview
- **Audit**: 4-Kategorie-Scores, Findings, Report + **Review-Freigabe-Button**
- **Redesign**: Taste-Dials (Variance/Motion/Density), Iterations-Verlauf, Feedback-Textarea
- **Paket**: Vorher/Nachher-Scores, Changelog, alle Downloads

### Prompt-Templates

`config/prompts/`:
- `audit_system.md` — 4 Kategorien + 27 Impeccable-Regeln
- `audit_user.md.j2` — Scraping-Daten inkl. Spacing/Motion/Components
- `redesign_direction.md` — UI/UX Pro Max Logik, Taste-Dials Interpretation, 20 UX-Guidelines
- `cover_letter.md.j2` — Anschreiben für Stage 6

## Wichtige Konventionen

- **Kein `print()`**: Immer `from shared import logger` verwenden
- **Pydantic überall**: Alle Datenstrukturen sind Pydantic v2-Modelle
- **Windows UTF-8**: `pipeline.py` setzt `sys.stdout.reconfigure(encoding='utf-8')` — kein ASCII-Breaking
- **Relative Pfade**: Stage-Code verwendet `Path("config/prompts")` relativ zum Projekt-Root
- **Vault-Pfad**: Fallback `output/vault/` wenn `VAULT_PATH` nicht gesetzt
- **shell=True bei subprocess**: Nötig für `npx` auf Windows (`.cmd`-Datei-Auflösung)

## Audit-Kategorien (v2 — 4 statt 3)

- `accessibility` — WCAG 2.1 AA + Landmark-Analyse
- `seo` — Meta-Tags, Heading-Hierarchie, Schema.org
- `ux_ui` — Visuelle Hierarchie, CTA-Klarheit, 27 Impeccable-Anti-Patterns
- `usability` — Touch-Targets, Responsiveness, Keyboard-Navigation, Breakpoints
