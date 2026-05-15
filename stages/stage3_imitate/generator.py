"""Generate 1:1 imitation React components informed by the full DESIGN.md context."""
import asyncio
from pathlib import Path

import anthropic

from shared import logger
from stages.stage1_scraper.models import ScrapedData


_SYSTEM_PROMPT = """Du bist ein Expert-Frontend-Entwickler. Deine Aufgabe ist es, eine bestehende Website
1:1 als modernes Next.js + TypeScript + Tailwind CSS Projekt nachzubilden — KEINE Verbesserungen,
nur eine akkurate Imitation.

Regeln:
- Verwende EXAKT die Farben, Fonts, Abstände und Struktur aus den Brand-Tokens und DESIGN.md
- Kein framer-motion, kein next/image (verwende <img>), keine externen Icon-Pakete
- Füge 'use client' hinzu wenn die Komponente onMouseEnter/onMouseLeave/onClick/useState verwendet — IMMER wenn Event-Handler vorhanden sind
- CSS-Animationen nur via Tailwind oder inline style, keine JS-Animationsbibliotheken
- Importiere brand tokens: `import { BRAND_COLORS, BRAND_FONTS, BRAND_SPACING } from '@/lib/brand';`
- BRAND_COLORS hat NUR diese flachen Keys: primary, secondary, accent, background, text, palette — KEINE verschachtelten Keys wie .white, .black, .border, .light, .dark
- BRAND_FONTS hat NUR: primary, secondary, bodySize, lineHeight — KEIN .body, .heading
- BRAND_SPACING hat NUR: scale (Array), radii (Array), shadow (string) — KEIN .lg, .md, .sm, .xl
- Für Weiß verwende '#FFFFFF', für Grau '#666666', für Abstände hardcode px-Werte (8px, 16px, 24px, 48px)
- Gib NUR validen TypeScript-Code zurück, keine Erklärungen, keine Markdown-Blöcke"""


_COMPONENT_PROMPTS = {
    "navigation": """Erstelle `src/components/Navigation.tsx` — 1:1 Imitation der Navigation von {domain}.

DESIGN SYSTEM:
{design_md}

Spezifische Daten von der Original-Website:
- Navigations-Typ: {nav_type}{nav_sticky}{nav_hamburger}
- Menü-Links (aus Sitemap): {nav_items}
- Logo/Domain: {domain}
- Primärfarbe: {primary}
- Schrift: {font_primary}

Baue: Responsive Navigation mit semantischem <nav>, Skip-Link "Zum Hauptinhalt", alle echten Menüpunkte.
Wenn Hamburger vorhanden: aria-expanded State mit useState ('use client').
Gib NUR den TypeScript-Code zurück.""",

    "hero": """Erstelle `src/components/Hero.tsx` — 1:1 Imitation der Hero-Sektion von {domain}.

DESIGN SYSTEM:
{design_md}

Spezifische Daten von der Original-Website:
- H1-Text: {h1}
- CTAs: {ctas}
- Wortanzahl Body-Text: {word_count}
- Primärfarbe: {primary}
- Akzentfarbe: {accent}
- Schrift: {font_primary}

Baue: Exakt ein <h1>, alle CTA-Buttons mit den originalen Texten, ähnliches Layout wie das Original.
Gib NUR den TypeScript-Code zurück.""",

    "features": """Erstelle `src/components/Features.tsx` — Imitation der Haupt-Content-Sektion von {domain}.

DESIGN SYSTEM:
{design_md}

Spezifische Daten:
- Domain: {domain}
- H2-Überschriften vorhanden: {h2_count}
- Cards/Tiles erkannt: {has_cards}
- Formulare: {form_count}
- Primärfarbe: {primary}
- Schrift: {font_primary}

Wenn Cards erkannt: Baue ein Card-Grid mit typischen Inhalten für {domain}.
Wenn Formular erkannt: Baue ein einfaches Kontaktformular.
Sonst: 3-spaltige Features/Benefits-Sektion mit branchenrelevanten Inhalten.
Gib NUR den TypeScript-Code zurück.""",

    "footer": """Erstelle `src/components/Footer.tsx` — 1:1 Imitation des Footers von {domain}.

DESIGN SYSTEM:
{design_md}

Spezifische Daten:
- Domain: {domain}
- Hat Impressum: {has_impressum}
- Hat Datenschutz: {has_privacy}
- Primärfarbe: {primary}
- Schrift: {font_primary}
- Nav-Links: {nav_items}

Baue: Semantisches <footer> mit role="contentinfo", Impressum-Link (PFLICHT), Datenschutz-Link (PFLICHT),
Copyright-Zeile, Nav-Links. Dunkler Hintergrund, weißer Text mit min. 4.5:1 Kontrast.
Gib NUR den TypeScript-Code zurück.""",
}


def _extract_code(text: str) -> str:
    for marker in ("```tsx", "```typescript", "```"):
        if marker in text:
            start = text.find(marker) + len(marker)
            if marker == "```" and text[start:start+2] in ("ts", "x\n", "\n"):
                start = text.find("\n", start) + 1
            end = text.find("```", start)
            return text[start:end].strip()
    return text.strip()


def _load_design_md(vault_folder_path: str | None) -> str:
    # Try vault first, then run scraped dir
    if vault_folder_path:
        p = Path(vault_folder_path) / "DESIGN.md"
        if p.exists():
            return p.read_text(encoding="utf-8")
    # Fallback: look for DESIGN.md in run dir's scraped folder or return minimal context
    return "# Design System\n(DESIGN.md nicht verfügbar — verwende Brand-Tokens)"


async def generate_components(
    project_dir: Path,
    data: ScrapedData,
    client: anthropic.Anthropic,
    model: str,
    vault_folder_path: str | None = None,
) -> None:
    components_dir = project_dir / "src" / "components"
    components_dir.mkdir(parents=True, exist_ok=True)

    design_md = _load_design_md(vault_folder_path)

    colors = data.colors.palette
    primary = colors[0].hex if colors else "#1a1a2e"
    accent = colors[2].hex if len(colors) > 2 else "#0f3460"
    font_primary = data.typography.families[0] if data.typography.families else "Inter"
    h1 = data.content.h1_texts[0] if data.content.h1_texts else data.domain
    ctas = ", ".join(f'"{c.text}"' for c in data.content.ctas[:4]) or '"Mehr erfahren"'
    nav_items = ", ".join(f'"{u}"' for u in data.sitemap.all_urls[:6]) or f'"{data.url}"'

    nav_sticky_str = " (sticky)" if data.components.nav_is_sticky else ""
    nav_hamburger_str = " mit Hamburger-Menu" if data.components.nav_has_hamburger else ""

    template_vars = {
        "domain": data.domain,
        "design_md": design_md[:3000],  # cap to avoid token overflow
        "primary": primary,
        "accent": accent,
        "font_primary": font_primary,
        "h1": h1,
        "ctas": ctas,
        "nav_items": nav_items,
        "nav_type": data.components.nav_type,
        "nav_sticky": nav_sticky_str,
        "nav_hamburger": nav_hamburger_str,
        "word_count": data.content.word_count,
        "h2_count": data.content.h2_count,
        "has_cards": str(data.components.has_cards),
        "form_count": data.components.form_count,
        "has_impressum": str(data.content.has_impressum),
        "has_privacy": str(data.content.has_privacy),
    }

    component_files = {
        "navigation": "Navigation.tsx",
        "hero": "Hero.tsx",
        "features": "Features.tsx",
        "footer": "Footer.tsx",
    }

    for section, filename in component_files.items():
        prompt = _COMPONENT_PROMPTS[section].format(**template_vars)
        logger.dim(f"  → Generiere {filename} (Imitat)...")

        response = await asyncio.to_thread(
            client.messages.create,
            model=model,
            max_tokens=4096,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        code = _extract_code(response.content[0].text)
        (components_dir / filename).write_text(code, encoding="utf-8")

    _write_page(project_dir, data)


def _write_page(project_dir: Path, data: ScrapedData) -> None:
    page_content = f"""import Navigation from "@/components/Navigation";
import Hero from "@/components/Hero";
import Features from "@/components/Features";
import Footer from "@/components/Footer";

export const metadata = {{
  title: "{data.meta.title or data.domain}",
  description: "{data.meta.description or f'Website von {data.domain}'}",
}};

export default function Home() {{
  return (
    <>
      <Navigation />
      <main id="main-content">
        <Hero />
        <Features />
      </main>
      <Footer />
    </>
  );
}}
"""
    page_path = project_dir / "src" / "app" / "page.tsx"
    page_path.write_text(page_content, encoding="utf-8")
