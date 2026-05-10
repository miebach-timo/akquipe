# akquipe

Automatisierte Akquise-Pipeline für UX/UI Freelancer. Du gibst eine URL ein — akquipe scrapt die Website, analysiert sie mit KI, baut sie modern nach und schnürt ein versandfertiges Angebot.

```
python pipeline.py run https://kundenwebsite.de
```

---

## Wie es funktioniert

```
URL eingeben
    │
    ▼
Stage 1: Scraper          Website analysieren (Farben, Fonts, Icons, Struktur)
    │
    ▼
Stage 2: Obsidian Vault   Alles strukturiert ablegen (Markdown + Mermaid)
    │
    ▼
Stage 3: KI-Audit         Claude prüft Barrierefreiheit, SEO und UX/UI
    │
    ▼
Stage 4: Rekonstruktion   Moderne Next.js-Version mit den Verbesserungen bauen
    │
    ▼
Stage 5: Paket            ZIP mit Audit-PDF, Anschreiben und Preisvorschlag
```

---

## Was rauskommt

Nach einem Pipeline-Run liegt in `output/<domain>/package/` ein ZIP bereit:

| Datei | Inhalt |
|---|---|
| `01_Audit_Report.pdf` | Professioneller Audit mit Scores und Befunden |
| `02_Anschreiben.md` | Personalisiertes Anschreiben an den Kunden |
| `03_Rekonstruierte_Website.zip` | Moderne Next.js-Version der Website |
| `04_Preisvorschlag.md` | Kalkuliertes Angebot basierend auf Aufwand |

---

## Setup

**Voraussetzungen:** Python 3.12+, Node.js 18+

```bash
# 1. Abhängigkeiten installieren
pip install -r requirements.txt
playwright install chromium

# 2. API-Key konfigurieren
cp .env.example .env
# .env öffnen und ANTHROPIC_API_KEY eintragen

# 3. Loslegen
python pipeline.py run https://beispielkunde.de
```

---

## CLI-Befehle

```bash
# Vollständige Pipeline (alle 5 Stages)
python pipeline.py run https://beispielkunde.de

# Nur Scraping + Vault + Audit (ohne Rekonstruktion — schneller)
python pipeline.py run https://beispielkunde.de --skip-reconstruct

# Nur bestimmte Stages ausführen
python pipeline.py run https://beispielkunde.de --stages 1,2,3

# Abgebrochenen Run fortsetzen (spart API-Kosten)
python pipeline.py resume beispielkunde_de_20260510_143022

# Alle bisherigen Runs auflisten
python pipeline.py list-runs
```

---

## Die 5 Stages im Detail

### Stage 1 — Website Scraper

Playwright öffnet die Website in einem Headless-Chrome-Browser und extrahiert:

- **Farben** — Komplette Farbpalette aus CSS-Variablen und Computed Styles, inkl. Kontrastverhältnisse (WCAG)
- **Typografie** — Schriftfamilien, Größen, Zeilenhöhe, Google Fonts Links
- **Icons** — Erkennt FontAwesome, Material Icons, Heroicons u.a. und erntet inline SVGs
- **Seitenstruktur** — BFS-Crawler bis Tiefe 3, max. 30 Seiten (konfigurierbar)
- **Inhalte** — H1–H3, CTAs, Meta-Tags, Alt-Texte, Impressum/Datenschutz-Links
- **Screenshots** — Full-Page, Above-the-Fold, Header, Main, Footer

Ergebnis: `output/<run>/scraped/data.json` + `screenshots/`

---

### Stage 2 — Obsidian Vault

Schreibt pro Kunde einen strukturierten Ordner in deinen Obsidian Vault (oder `output/vault/`):

```
akquipe/beispielkunde_de/
  _Overview.md        Index mit Dataview-Frontmatter und Quick-Stats
  Colors.md           Farbpalette + Kontrast-Tabelle
  Typography.md       Schriften + WCAG-Hinweise
  Icons.md            Bibliotheken + SVG-Inventar
  Page-Hierarchy.md   Sitemap als verschachtelte Liste
  User-Flow.md        Mermaid-Flowchart der Navigation
  Screenshots.md      Eingebettete Screenshot-Galerie
  Audit-Report.md     Wird nach Stage 3 automatisch befüllt
  assets/
    screenshots/
    icons/
```

Alle Notes sind untereinander verlinkt (`[[Wikilinks]]`) und Dataview-kompatibel — du kannst dir eine Übersicht aller Kunden per Dataview-Query erstellen.

---

### Stage 3 — KI-Audit Agent

Claude (`claude-sonnet-4-6`) analysiert die Scraper-Daten mit einem strukturierten Tool-Use Loop. Der Agent ruft drei Tools auf:

- `record_finding` — Erfasst jeden Befund mit Schweregrad, WCAG-Kriterium, Ist-/Soll-Wert
- `set_category_score` — Bewertet jede Kategorie 0–100
- `generate_report` — Schreibt Executive Summary und Top-Priorität

**Geprüfte Kategorien:**

| Kategorie | Was wird geprüft |
|---|---|
| Barrierefreiheit (WCAG 2.1 AA) | Farbkontraste, Alt-Texte, Semantik, Keyboard-Navigation, ARIA |
| SEO | Title, Meta-Description, Heading-Hierarchie, Schema.org, Open Graph |
| UX/UI | Visuelle Hierarchie, CTA-Klarheit, Mobile Responsiveness, Design-Modernität |

Ergebnis: `audit_report.md` (in Vault) + `audit_report.pdf` (für Kunden)

---

### Stage 4 — Website Rekonstruktion

Baut eine moderne Version der Website mit den Audit-Verbesserungen:

1. `create-next-app` mit TypeScript, Tailwind CSS, App Router
2. Brand-Tokens aus dem Scraping → `src/lib/brand.ts` + CSS-Variablen
3. Claude generiert Komponenten section-by-section:
   - `Navigation.tsx` — Accessible Navbar mit Skip-Link, aria-expanded, Fokus-Indikatoren
   - `Hero.tsx` — Kontrastreiche Hero-Section mit klarem primären CTA
   - `Footer.tsx` — Footer mit Impressum + Datenschutz (DSGVO-konform)

Das Next.js-Projekt ist sofort lauffähig (`npm install && npm run dev`).

---

### Stage 5 — Kundenpaket

Bündelt alles in ein versandfertiges ZIP:

- **Audit-Report** als PDF — professionell, mit Scoring-Tabelle und priorisierten Findings
- **Anschreiben** — personalisiertes Anschreiben aus Template, mit Audit-Scores
- **Rekonstruierte Website** — gezipptes Next.js-Projekt
- **Preisvorschlag** — heuristisch kalkuliert auf Basis Seitenanzahl + Findings + Aufwand

Der Preis wird automatisch aus deinem Tagessatz (`.env: FREELANCER_DAY_RATE`) und dem Projektaufwand berechnet.

---

## Konfiguration (.env)

```env
# Pflichtfeld
ANTHROPIC_API_KEY=sk-ant-...

# Optional — Standard-Werte sind gut für den Einstieg
VAULT_PATH=C:/Users/dein-name/Documents/ObsidianVault   # leer = output/vault/
OUTPUT_DIR=output
SCRAPER_MAX_PAGES=30
SCRAPER_MAX_DEPTH=3
FREELANCER_DAY_RATE=800
AUDIT_MODEL=claude-sonnet-4-6
RECONSTRUCT_MODEL=claude-haiku-4-5-20251001
```

---

## Projektstruktur

```
akquipe/
├── pipeline.py                    # CLI (Typer)
├── config/
│   ├── settings.py                # Pydantic Settings
│   └── prompts/                   # Jinja2 Templates für Claude-Prompts
├── shared/
│   ├── run_state.py               # RunState JSON — verbindet alle Stages
│   ├── logger.py                  # Rich-Logger
│   └── utils.py
├── stages/
│   ├── stage1_scraper/            # Playwright + Extraktoren
│   ├── stage2_vault/              # Obsidian Note-Builder
│   ├── stage3_audit/              # Claude Audit-Agent
│   ├── stage4_reconstruct/        # Next.js Generator
│   └── stage5_package/            # ZIP-Packager + Preismodell
└── output/                        # Alle Run-Artefakte (gitignored)
```

Jeder Run speichert seinen Zustand in `output/<run-id>/run_state.json`. Das erlaubt es, abgebrochene Runs fortzusetzen ohne API-Kosten zu wiederholen.

---

## Tech Stack

| Bereich | Technologie |
|---|---|
| Scraping | Python + Playwright (Chromium) |
| KI-Agent | Anthropic Claude API (tool_use) |
| Datenmodelle | Pydantic v2 |
| CLI | Typer + Rich |
| Templates | Jinja2 |
| Rekonstruktion | Next.js 15 + Tailwind CSS 4 + TypeScript |
| PDF-Export | npx md-to-pdf |

---

## Lizenz

MIT
