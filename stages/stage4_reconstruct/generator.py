import asyncio
import anthropic
from pathlib import Path

from shared import logger
from stages.stage1_scraper.models import ScrapedData


_SECTION_PROMPTS = {
    "navigation": """Erstelle eine moderne React Navigation-Komponente (`src/components/Navigation.tsx`) für {domain}.

Brand:
- Primärfarbe: {primary}
- Schrift: {font}

Inhalte von der Original-Website:
- Seiten im Menü: {nav_items}
- CTAs: {ctas}

Anforderungen (aus Audit):
- WCAG AA: Kontrastverhältnis min. 4.5:1 für Text
- Semantisches HTML: <nav> mit aria-label, <ul>/<li> für Menüpunkte
- Skip-Link "Zum Hauptinhalt" als erstes Element (für Keyboard-Navigation)
- Mobile-Hamburger-Menü mit aria-expanded
- Alle Links haben erkennbaren Fokus-Indikator (outline oder ring)
- Tailwind CSS + TypeScript

Importiere brand tokens so: `import {{ BRAND_COLORS, BRAND_FONTS }} from '@/lib/brand';`
Kein externes Icon-Package, kein framer-motion. Gib NUR den TypeScript-Code zurück.""",

    "hero": """Erstelle eine moderne React Hero-Komponente (`src/components/Hero.tsx`) für {domain}.

Brand:
- Primärfarbe: {primary}
- Akzentfarbe: {accent}
- Schrift: {font}

Inhalte von der Original-Website:
- H1: {h1}
- CTAs: {ctas}
- Wortanzahl Body: {word_count}

Anforderungen (aus Audit):
- Genau ein <h1>-Tag
- Primärer CTA mit aussagekräftigem Text (kein "Klicken Sie hier")
- Kontrastreiche Farben (WCAG AA)
- Responsive (mobile-first mit Tailwind)
- Nur CSS-Animationen, kein framer-motion

Importiere brand tokens so: `import {{ BRAND_COLORS, BRAND_FONTS }} from '@/lib/brand';`
Gib NUR den TypeScript-Code zurück.""",

    "footer": """Erstelle einen modernen React Footer (`src/components/Footer.tsx`) für {domain}.

Inhalte:
- Domain: {domain}
- Hat Impressum: {has_impressum}
- Hat Datenschutz: {has_privacy}

Anforderungen (aus Audit):
- Impressum-Link MUSS vorhanden sein
- Datenschutz-Link MUSS vorhanden sein
- Semantisches <footer> mit role="contentinfo"
- Copyright-Zeile
- Kontrast prüfen (weißer Text auf dunklem Hintergrund: mindestens 4.5:1)

Importiere brand tokens so: `import {{ BRAND_COLORS, BRAND_FONTS }} from '@/lib/brand';`
Gib NUR den TypeScript-Code zurück.""",
}


def _extract_code(response_text: str) -> str:
    """Extract TypeScript code from Claude response."""
    if "```tsx" in response_text:
        start = response_text.find("```tsx") + 6
        end = response_text.find("```", start)
        return response_text[start:end].strip()
    if "```typescript" in response_text:
        start = response_text.find("```typescript") + 13
        end = response_text.find("```", start)
        return response_text[start:end].strip()
    if "```" in response_text:
        start = response_text.find("```") + 3
        end = response_text.find("```", start)
        return response_text[start:end].strip()
    return response_text.strip()


async def generate_components(project_dir: Path, data: ScrapedData, client: anthropic.Anthropic, model: str) -> None:
    components_dir = project_dir / "src" / "components"
    components_dir.mkdir(parents=True, exist_ok=True)

    colors = data.colors.palette
    primary = colors[0].hex if colors else "#1a1a2e"
    accent = colors[2].hex if len(colors) > 2 else "#0f3460"
    font = data.typography.families[0] if data.typography.families else "Inter"
    h1 = data.content.h1_texts[0] if data.content.h1_texts else data.domain
    ctas = ", ".join(f'"{c.text}"' for c in data.content.ctas[:3]) or '"Mehr erfahren"'
    nav_items = ", ".join(data.sitemap.all_urls[:6]) or data.url

    template_vars = {
        "domain": data.domain,
        "primary": primary,
        "accent": accent,
        "font": font,
        "h1": h1,
        "ctas": ctas,
        "nav_items": nav_items,
        "word_count": data.content.word_count,
        "has_impressum": str(data.content.has_impressum),
        "has_privacy": str(data.content.has_privacy),
    }

    component_files = {
        "navigation": "Navigation.tsx",
        "hero": "Hero.tsx",
        "footer": "Footer.tsx",
    }

    for section, filename in component_files.items():
        prompt = _SECTION_PROMPTS[section].format(**template_vars)
        logger.dim(f"  → Generiere {filename}...")

        response = await asyncio.to_thread(
            client.messages.create,
            model=model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        code = _extract_code(response.content[0].text)
        (components_dir / filename).write_text(code, encoding="utf-8")

    _write_page(project_dir, data)


def _write_page(project_dir: Path, data: ScrapedData) -> None:
    page_content = f"""import Navigation from "@/components/Navigation";
import Hero from "@/components/Hero";
import Footer from "@/components/Footer";

export const metadata = {{
  title: "{data.meta.title or data.domain} — Modernisiert",
  description: "{data.meta.description or f'Modernisierte Website von {data.domain}'}",
}};

export default function Home() {{
  return (
    <>
      <Navigation />
      <main id="main-content">
        <Hero />
      </main>
      <Footer />
    </>
  );
}}
"""
    page_path = project_dir / "src" / "app" / "page.tsx"
    page_path.write_text(page_content, encoding="utf-8")
