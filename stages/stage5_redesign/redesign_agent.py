"""Stage 5 Redesign — iterative redesign with UI/UX Pro Max reasoning and Taste dials."""
import asyncio
import subprocess
from datetime import datetime
from pathlib import Path

import anthropic

from shared import logger
from shared.run_state import RunState, Status, RedesignIteration, RedesignParams
from stages.stage1_scraper.scraper import load_scraped_data
from stages.stage1_scraper.models import ScrapedData
from stages.stage3_imitate.brand_writer import write_brand_tokens


_COMPONENT_PROMPTS = {
    "navigation": """Erstelle `src/components/Navigation.tsx` — verbessertes Redesign der Navigation von {domain}.

{direction_prompt}

DESIGN SYSTEM:
{design_md}

Original-Website Daten:
- Navigations-Typ: {nav_type}
- Menü-Links: {nav_items}
- Primärfarbe (verbessert): {primary}
- Schrift: {font_primary}

KORREKTUREN aus Audit (PFLICHT):
{audit_corrections}

Erstelle eine semantisch korrekte, accessible Navigation mit Skip-Link, aria-expanded Hamburger (useState),
sichtbarem Focus-Ring und WCAG AA Kontrast.
Gib NUR den TypeScript-Code zurück.""",

    "hero": """Erstelle `src/components/Hero.tsx` — verbessertes Redesign der Hero-Sektion von {domain}.

{direction_prompt}

DESIGN SYSTEM:
{design_md}

Original-Website Daten:
- H1-Text: {h1}
- CTAs: {ctas}
- Primärfarbe (verbessert): {primary}
- Akzentfarbe: {accent}
- Schrift: {font_primary}

KORREKTUREN aus Audit (PFLICHT):
{audit_corrections}

Erstelle: Genau ein <h1>, primärer CTA groß und auffällig (min. 44px Höhe), WCAG AA Kontrast.
Motion-Intensität {motion_intensity}/10 — entsprechend animieren oder statisch lassen.
Gib NUR den TypeScript-Code zurück.""",

    "features": """Erstelle `src/components/Features.tsx` — Redesign der Haupt-Content-Sektion von {domain}.

{direction_prompt}

DESIGN SYSTEM:
{design_md}

Original-Website Daten:
- Branche/Domain: {domain}
- Cards erkannt: {has_cards}
- Visual Density: {visual_density}/10

KORREKTUREN aus Audit (PFLICHT):
{audit_corrections}

Erstelle: Eine professionelle Features/Benefits-Sektion passend zur Branche.
Wenn density hoch (>6): kompaktes Grid. Wenn niedrig (<4): großzügige Karten mit viel Whitespace.
Gib NUR den TypeScript-Code zurück.""",

    "footer": """Erstelle `src/components/Footer.tsx` — Redesign des Footers von {domain}.

{direction_prompt}

DESIGN SYSTEM:
{design_md}

Original-Website Daten:
- Hat Impressum: {has_impressum}
- Hat Datenschutz: {has_privacy}
- Nav-Links: {nav_items}
- Primärfarbe: {primary}

PFLICHT: Impressum-Link, Datenschutz-Link, Copyright.
Dunkler Hintergrund, weißer Text mit min. 4.5:1 Kontrast.
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
    if vault_folder_path:
        p = Path(vault_folder_path) / "DESIGN.md"
        if p.exists():
            return p.read_text(encoding="utf-8")
    return "# Design System\n(DESIGN.md nicht verfügbar)"


def _load_audit_report(state: RunState) -> str:
    if state.audit.report_md_path:
        p = Path(state.audit.report_md_path)
        if p.exists():
            return p.read_text(encoding="utf-8")
    return "Kein Audit-Report verfügbar."


def _build_audit_corrections(audit_md: str) -> str:
    lines = audit_md.split("\n")
    corrections = []
    for i, line in enumerate(lines):
        if "🔴" in line or "🟠" in line:
            title = line.strip("# ").strip()
            corrections.append(f"- BEHEBEN: {title}")
        if len(corrections) >= 10:
            break
    return "\n".join(corrections) if corrections else "— Keine kritischen Befunde"


def _build_direction_prompt(params: RedesignParams, user_feedback: str, manual_review_notes: str = "") -> str:
    variance_desc = {
        range(1, 4): "KONSERVATIV: Nur Kontrast und Accessibility fixen, Struktur beibehalten",
        range(4, 7): "AUSGEWOGEN: Neue Section-Layouts, verbesserte Typografie, moderne Komponenten",
        range(7, 11): "EXPERIMENTELL: Neue Farbpalette, mutige Typografie, innovatives Layout",
    }
    motion_desc = {
        range(1, 3): "KEIN JS: Nur CSS :hover transitions (150ms)",
        range(3, 7): "SUBTIL: CSS-Animationen mit @keyframes (fade-in, slide-up)",
        range(7, 11): "LEBENDIG: CSS IntersectionObserver oder Framer Motion für Scroll-Animationen",
    }
    density_desc = {
        range(1, 4): "LUFTIG: Viel Whitespace (section padding: 120px), große Schrift",
        range(4, 7): "AUSGEWOGEN: Standard-Abstände (section padding: 80px)",
        range(7, 11): "DICHT: Kompaktes Layout (section padding: 48px), viele Elemente",
    }

    def _match(d, val):
        for r, desc in d.items():
            if val in r:
                return desc
        return list(d.values())[1]

    lines = []

    if manual_review_notes:
        lines.append(f"=== MANUELLE REVIEW-ANWEISUNGEN (HÖCHSTE PRIORITÄT — VOR ALLEM ANDEREN UMSETZEN) ===")
        lines.append(manual_review_notes)
        lines.append("=== ENDE REVIEW-ANWEISUNGEN ===\n")

    lines += [
        f"Design-Variance ({params.design_variance}/10): {_match(variance_desc, params.design_variance)}",
        f"Motion-Intensität ({params.motion_intensity}/10): {_match(motion_desc, params.motion_intensity)}",
        f"Visual-Density ({params.visual_density}/10): {_match(density_desc, params.visual_density)}",
        f"Style-Direction: {params.style_direction}",
    ]
    if user_feedback:
        lines.append(f"\nNutzer-Feedback zur letzten Iteration: {user_feedback}")
    return "\n".join(lines)


async def run_redesign_iteration(
    state: RunState,
    settings,
    params: RedesignParams,
    user_feedback: str = "",
) -> RunState:
    state.redesign.status = Status.RUNNING

    try:
        data = load_scraped_data(state, settings.output_dir)
        run_dir = state.run_dir(settings.output_dir)
        iteration_num = state.redesign.current_iteration + 1
        project_dir = run_dir / "redesign" / f"iteration_{iteration_num}"

        logger.info(f"Starte Redesign-Iteration {iteration_num}...")
        project_dir.parent.mkdir(parents=True, exist_ok=True)

        if not project_dir.exists():
            result = subprocess.run(
                [
                    "npx", "create-next-app@latest", str(project_dir),
                    "--typescript", "--tailwind", "--app",
                    "--no-git", "--yes", "--src-dir",
                    "--import-alias", "@/*",
                ],
                capture_output=True, text=True, timeout=300, shell=True,
            )
            if result.returncode != 0:
                raise RuntimeError(f"create-next-app fehlgeschlagen:\n{result.stderr or result.stdout[:500]}")
        else:
            logger.dim(f"  → Projektverzeichnis existiert bereits, überspringe create-next-app")

        write_brand_tokens(project_dir, data)

        design_md = _load_design_md(state.vault.folder_path)
        audit_md = _load_audit_report(state)
        audit_corrections = _build_audit_corrections(audit_md)
        direction_prompt = _build_direction_prompt(
            params, user_feedback,
            manual_review_notes=state.audit.manual_review_notes,
        )

        colors = data.colors.palette
        primary = colors[0].hex if colors else "#1a1a2e"
        accent = colors[2].hex if len(colors) > 2 else "#0f3460"
        font_primary = data.typography.families[0] if data.typography.families else "Inter"
        h1 = data.content.h1_texts[0] if data.content.h1_texts else data.domain
        ctas = ", ".join(f'"{c.text}"' for c in data.content.ctas[:4]) or '"Jetzt starten"'
        nav_items = ", ".join(f'"{u}"' for u in data.sitemap.all_urls[:6]) or f'"{data.url}"'

        direction_system = (Path("config/prompts") / "redesign_direction.md").read_text(encoding="utf-8")

        template_vars = {
            "domain": data.domain,
            "design_md": design_md[:2000],
            "direction_prompt": direction_prompt,
            "audit_corrections": audit_corrections,
            "primary": primary,
            "accent": accent,
            "font_primary": font_primary,
            "h1": h1,
            "ctas": ctas,
            "nav_items": nav_items,
            "nav_type": data.components.nav_type,
            "has_cards": str(data.components.has_cards),
            "has_impressum": str(data.content.has_impressum),
            "has_privacy": str(data.content.has_privacy),
            "motion_intensity": params.motion_intensity,
            "visual_density": params.visual_density,
        }

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        components_dir = project_dir / "src" / "components"
        components_dir.mkdir(parents=True, exist_ok=True)

        component_files = {
            "navigation": "Navigation.tsx",
            "hero": "Hero.tsx",
            "features": "Features.tsx",
            "footer": "Footer.tsx",
        }

        for section, filename in component_files.items():
            prompt = _COMPONENT_PROMPTS[section].format(**template_vars)
            logger.dim(f"  → Generiere {filename} (Redesign Iter. {iteration_num})...")

            response = await asyncio.to_thread(
                client.messages.create,
                model=settings.reconstruct_model,
                max_tokens=4096,
                system=direction_system,
                messages=[{"role": "user", "content": prompt}],
            )
            code = _extract_code(response.content[0].text)
            (components_dir / filename).write_text(code, encoding="utf-8")

        _write_page(project_dir, data)

        iteration = RedesignIteration(
            iteration=iteration_num,
            project_path=str(project_dir),
            params=params,
            user_feedback=user_feedback,
            created_at=datetime.now().isoformat(),
        )
        state.redesign.iterations.append(iteration)
        state.redesign.current_iteration = iteration_num
        state.redesign.project_path = str(project_dir)
        state.redesign.status = Status.DONE

        logger.success(f"Redesign Iteration {iteration_num} abgeschlossen: {project_dir}")

    except Exception as e:
        state.redesign.status = Status.FAILED
        state.redesign.error = str(e)
        logger.error(f"Redesign fehlgeschlagen: {e}")
        raise

    return state


async def run_redesign(state: RunState, settings) -> RunState:
    params = RedesignParams()
    return await run_redesign_iteration(state, settings, params)


def _write_page(project_dir: Path, data: ScrapedData) -> None:
    page_content = f"""import Navigation from "@/components/Navigation";
import Hero from "@/components/Hero";
import Features from "@/components/Features";
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
        <Features />
      </main>
      <Footer />
    </>
  );
}}
"""
    (project_dir / "src" / "app" / "page.tsx").write_text(page_content, encoding="utf-8")
