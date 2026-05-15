"""Stage 3: Imitate — scaffold a Next.js project that faithfully reproduces the original website."""
import subprocess
from pathlib import Path

import anthropic

from shared import logger
from shared.run_state import RunState, Status
from stages.stage1_scraper.scraper import load_scraped_data
from stages.stage3_imitate.brand_writer import write_brand_tokens
from stages.stage3_imitate.generator import generate_components


async def run_imitate(state: RunState, settings) -> RunState:
    state.imitate.status = Status.RUNNING

    try:
        data = load_scraped_data(state, settings.output_dir)
        run_dir = state.run_dir(settings.output_dir)
        project_dir = run_dir / "imitate"

        logger.info(f"Erstelle Next.js-Imitat in {project_dir}...")
        project_dir.parent.mkdir(parents=True, exist_ok=True)

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
            shell=True,
        )

        if result.returncode != 0:
            raise RuntimeError(f"create-next-app fehlgeschlagen:\n{result.stderr[:500]}")

        logger.success("Next.js-Projekt erstellt")

        logger.dim("  → Schreibe Brand-Tokens (inkl. Spacing)...")
        write_brand_tokens(project_dir, data)

        logger.dim("  → Generiere Imitat-Komponenten mit Claude...")
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        await generate_components(
            project_dir,
            data,
            client,
            settings.reconstruct_model,
            vault_folder_path=state.vault.folder_path,
        )

        _write_readme(project_dir, data, state)

        state.imitate.status = Status.DONE
        state.imitate.project_path = str(project_dir)
        logger.success(f"Imitat abgeschlossen: {project_dir}")

    except subprocess.TimeoutExpired:
        state.imitate.status = Status.FAILED
        state.imitate.error = "create-next-app Timeout (>5 min)"
        logger.error("create-next-app hat zu lange gedauert. Node.js installiert?")
        raise
    except Exception as e:
        state.imitate.status = Status.FAILED
        state.imitate.error = str(e)
        logger.error(f"Imitat fehlgeschlagen: {e}")
        raise

    return state


def _write_readme(project_dir: Path, data, state: RunState) -> None:
    readme = f"""# {data.domain} — Imitat (1:1 Replica)

Automatisch rekonstruiert von akquipe (Run: {state.run_id})
**Zweck:** 1:1-Imitation der Originalseite als Basis für den Audit-Vergleich.

## Starten

```bash
npm install
npm run dev
```

Dann: http://localhost:3000

## Brand-Tokens

`src/lib/brand.ts` enthält alle Farb-, Schrift- und Spacing-Tokens.

## Komponenten

- `src/components/Navigation.tsx` — Navbar (1:1 Original)
- `src/components/Hero.tsx` — Hero Section
- `src/components/Features.tsx` — Haupt-Content-Sektion
- `src/components/Footer.tsx` — Footer mit Impressum/Datenschutz

## Hinweis

Dieses Projekt imitiert nur — Verbesserungen folgen in Stage 5 (Redesign).
"""
    (project_dir / "README.md").write_text(readme, encoding="utf-8")
