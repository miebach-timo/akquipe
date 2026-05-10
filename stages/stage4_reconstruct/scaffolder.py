import asyncio
import subprocess
from pathlib import Path

import anthropic

from shared import logger
from shared.run_state import RunState, Status
from shared.utils import safe_filename
from stages.stage1_scraper.scraper import load_scraped_data
from stages.stage4_reconstruct.brand_writer import write_brand_tokens
from stages.stage4_reconstruct.generator import generate_components


async def run_reconstruct(state: RunState, settings) -> RunState:
    state.reconstruct.status = Status.RUNNING

    try:
        data = load_scraped_data(state, settings.output_dir)
        run_dir = state.run_dir(settings.output_dir)
        project_dir = run_dir / "reconstructed"

        logger.info(f"Erstelle Next.js-Projekt in {project_dir}...")
        project_dir.parent.mkdir(parents=True, exist_ok=True)

        # create-next-app
        result = subprocess.run(
            [
                "npx", "create-next-app@latest", str(project_dir),
                "--typescript",
                "--tailwind",
                "--app",
                "--no-git",
                "--yes",
                "--src-dir",
                "--import-alias", "@/*",
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode != 0:
            raise RuntimeError(f"create-next-app fehlgeschlagen:\n{result.stderr[:500]}")

        logger.success("Next.js-Projekt erstellt")

        logger.dim("  → Schreibe Brand-Tokens...")
        write_brand_tokens(project_dir, data)

        logger.dim("  → Generiere Komponenten mit Claude...")
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        await generate_components(project_dir, data, client, settings.reconstruct_model)

        _write_readme(project_dir, data, state)

        state.reconstruct.status = Status.DONE
        state.reconstruct.project_path = str(project_dir)
        logger.success(f"Rekonstruktion abgeschlossen: {project_dir}")

    except subprocess.TimeoutExpired:
        state.reconstruct.status = Status.FAILED
        state.reconstruct.error = "create-next-app Timeout (>5 min)"
        logger.error("create-next-app hat zu lange gedauert. Node.js installiert?")
        raise
    except Exception as e:
        state.reconstruct.status = Status.FAILED
        state.reconstruct.error = str(e)
        logger.error(f"Rekonstruktion fehlgeschlagen: {e}")
        raise

    return state


def _write_readme(project_dir: Path, data, state: RunState) -> None:
    readme = f"""# {data.domain} — Modernisiert

Automatisch rekonstruiert von akquipe (Run: {state.run_id})

## Starten

```bash
npm install
npm run dev
```

Dann: http://localhost:3000

## Brand-Tokens

Alle Farb- und Schrift-Tokens: `src/lib/brand.ts`

## Komponenten

- `src/components/Navigation.tsx` — Accessible Navbar
- `src/components/Hero.tsx` — Hero Section
- `src/components/Footer.tsx` — Footer mit Impressum/Datenschutz

## Audit-Verbesserungen implementiert

- WCAG 2.1 AA Kontrastverhältnisse
- Semantisches HTML (nav, main, footer, heading-Hierarchie)
- Skip-Link für Keyboard-Navigation
- Meta-Tags (title, description)
- Impressum + Datenschutz-Links im Footer
"""
    (project_dir / "README.md").write_text(readme, encoding="utf-8")
