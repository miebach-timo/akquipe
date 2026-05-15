"""akquipe -- UX/UI Freelancer Akquise-Pipeline v2"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Ensure UTF-8 output on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf8"):
    sys.stderr.reconfigure(encoding="utf-8")

import typer
from rich.table import Table

from config.settings import get_settings
from shared import logger
from shared.run_state import RunState, Status, RedesignParams
from shared.utils import domain_from_url, run_id_from_url

app = typer.Typer(
    name="akquipe",
    help="UX/UI Freelancer Pipeline: Scrape → Vault → Imitate → Audit → Redesign → Package",
    no_args_is_help=True,
)


def _parse_stages(stages_str: str) -> set[int]:
    try:
        return {int(s.strip()) for s in stages_str.split(",")}
    except ValueError:
        raise typer.BadParameter(f"Ungültige Stage-Angabe: '{stages_str}'. Beispiel: '1,2,3'")


@app.command()
def run(
    url: str = typer.Argument(..., help="Ziel-URL der Website (z.B. https://example.com)"),
    stages: str = typer.Option("1,2,3,4,5,6", "--stages", "-s", help="Kommaseparierte Stage-Nummern (1–6)"),
    run_id: Optional[str] = typer.Option(None, "--run-id", help="Bestehenden Run fortsetzen"),
    vault_path: Optional[Path] = typer.Option(None, "--vault-path", help="Obsidian Vault-Pfad"),
    output_dir: Optional[Path] = typer.Option(None, "--output-dir", help="Ausgabeverzeichnis"),
) -> None:
    """Vollständige Pipeline für eine Website starten.

    Stage 1: Scrape  |  Stage 2: Vault  |  Stage 3: Imitate
    Stage 4: Audit   |  Stage 5: Redesign  |  Stage 6: Package
    """
    settings = get_settings()

    if output_dir:
        settings.output_dir = output_dir
    if vault_path:
        settings.vault_path = vault_path

    active_stages = _parse_stages(stages)

    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"

    domain = domain_from_url(url)
    current_run_id = run_id or run_id_from_url(url)

    state = RunState.load_or_create(
        run_id=current_run_id,
        url=url,
        domain=domain,
        output_dir=settings.output_dir,
    )

    logger.console.rule(f"[bold cyan]akquipe v2[/bold cyan] — {url}")
    logger.info(f"Run ID: {current_run_id}")
    logger.info(f"Aktive Stages: {sorted(active_stages)}")
    logger.info(f"Output: {settings.output_dir / current_run_id}")

    asyncio.run(_execute_pipeline(state, active_stages, settings))


async def _execute_pipeline(state: RunState, active_stages: set[int], settings) -> None:
    run_dir = state.run_dir(settings.output_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    if 1 in active_stages and state.scraper.status != Status.DONE:
        logger.stage(1, "Website scrapen")
        from stages.stage1_scraper.scraper import run_scraper
        state = await run_scraper(state, settings)
        state.save(settings.output_dir)

    if 2 in active_stages and state.vault.status != Status.DONE:
        if state.scraper.status != Status.DONE:
            logger.warning("Stage 2 übersprungen — Stage 1 nicht abgeschlossen.")
        else:
            logger.stage(2, "Obsidian Vault befüllen + DESIGN.md")
            from stages.stage2_vault.vault_writer import run_vault_writer
            state = run_vault_writer(state, settings)
            state.save(settings.output_dir)

    if 3 in active_stages and state.imitate.status != Status.DONE:
        if state.scraper.status != Status.DONE:
            logger.warning("Stage 3 übersprungen — Stage 1 nicht abgeschlossen.")
        else:
            logger.stage(3, "Website imitieren (1:1 Replica)")
            from stages.stage3_imitate.scaffolder import run_imitate
            state = await run_imitate(state, settings)
            state.save(settings.output_dir)

    if 4 in active_stages and state.audit.status != Status.DONE:
        if state.scraper.status != Status.DONE:
            logger.warning("Stage 4 übersprungen — Stage 1 nicht abgeschlossen.")
        else:
            logger.stage(4, "KI-Audit durchführen (4 Kategorien)")
            from stages.stage4_audit.agent import run_audit
            state = await run_audit(state, settings)
            state.save(settings.output_dir)
            if not state.audit.manual_review_approved:
                logger.warning(
                    "Audit abgeschlossen. Bitte Review im Dashboard freigeben:\n"
                    "  streamlit run app.py\n"
                    "  Oder: python pipeline.py approve " + state.run_id
                )
                if 5 in active_stages or 6 in active_stages:
                    logger.warning("Stage 5+6 pausiert bis Audit-Review freigegeben.")
                    return

    if 5 in active_stages and state.redesign.status != Status.DONE:
        if state.scraper.status != Status.DONE:
            logger.warning("Stage 5 übersprungen — Stage 1 nicht abgeschlossen.")
        elif not state.audit.manual_review_approved:
            logger.warning(
                "Stage 5 übersprungen — Audit-Review noch nicht freigegeben.\n"
                "Freigeben: python pipeline.py approve " + state.run_id
            )
        else:
            logger.stage(5, "Website neu gestalten (Redesign)")
            from stages.stage5_redesign.redesign_agent import run_redesign
            state = await run_redesign(state, settings)
            state.save(settings.output_dir)

    if 6 in active_stages and state.package.status != Status.DONE:
        logger.stage(6, "Kundenpaket schnüren")
        from stages.stage6_package.packager import run_packager
        state = run_packager(state, settings)
        state.save(settings.output_dir)

    _print_summary(state)


def _print_summary(state: RunState) -> None:
    logger.console.rule("[bold green]Pipeline abgeschlossen[/bold green]")

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Stage", style="dim")
    table.add_column("Status")
    table.add_column("Details")

    def _icon(status: Status) -> str:
        return {"done": "✅", "failed": "❌", "skipped": "⏭", "pending": "⏸", "running": "🔄"}.get(status, "?")

    table.add_row("1 Scraper", _icon(state.scraper.status), f"{state.scraper.pages_crawled} Seiten gecrawlt")
    table.add_row("2 Vault", _icon(state.vault.status), state.vault.folder_path or "—")
    table.add_row("3 Imitat", _icon(state.imitate.status), state.imitate.project_path or "—")

    scores = state.audit.scores
    review = " (Review: ✅)" if state.audit.manual_review_approved else " (Review: ⏳)"
    score_str = f"A:{scores.get('accessibility','—')} S:{scores.get('seo','—')} UX:{scores.get('ux_ui','—')} US:{scores.get('usability','—')}{review}"
    table.add_row("4 Audit", _icon(state.audit.status), score_str)

    iterations = len(state.redesign.iterations)
    table.add_row("5 Redesign", _icon(state.redesign.status), f"{iterations} Iteration(en)" if iterations else (state.redesign.project_path or "—"))
    table.add_row("6 Paket", _icon(state.package.status), state.package.zip_path or "—")

    logger.console.print(table)

    if state.package.zip_path:
        logger.success(f"Paket bereit: {state.package.zip_path}")
    if state.package.pricing_eur:
        logger.info(f"Preisvorschlag: {state.package.pricing_eur:,.0f} EUR")


@app.command()
def resume(
    run_id: str = typer.Argument(..., help="Run-ID aus 'list-runs'"),
    stages: str = typer.Option("1,2,3,4,5,6", "--stages", "-s"),
    output_dir: Optional[Path] = typer.Option(None, "--output-dir"),
) -> None:
    """Abgebrochenen oder partiellen Run fortsetzen."""
    settings = get_settings()
    if output_dir:
        settings.output_dir = output_dir

    try:
        state = RunState.load(run_id, settings.output_dir)
    except FileNotFoundError:
        logger.error(f"Run '{run_id}' nicht gefunden in {settings.output_dir}")
        raise typer.Exit(1)

    active_stages = _parse_stages(stages)
    logger.info(f"Setze Run fort: {run_id}")
    asyncio.run(_execute_pipeline(state, active_stages, settings))


@app.command()
def approve(
    run_id: str = typer.Argument(..., help="Run-ID aus 'list-runs'"),
    notes: str = typer.Option("", "--notes", "-n", help="Manuelle Anmerkungen zum Audit"),
    output_dir: Optional[Path] = typer.Option(None, "--output-dir"),
) -> None:
    """Audit-Review freigeben und Stages 5+6 fortsetzen."""
    settings = get_settings()
    if output_dir:
        settings.output_dir = output_dir

    try:
        state = RunState.load(run_id, settings.output_dir)
    except FileNotFoundError:
        logger.error(f"Run '{run_id}' nicht gefunden in {settings.output_dir}")
        raise typer.Exit(1)

    if state.audit.status != Status.DONE:
        logger.error("Audit noch nicht abgeschlossen. Zuerst Stage 4 ausführen.")
        raise typer.Exit(1)

    state.audit.manual_review_approved = True
    state.audit.manual_review_notes = notes
    state.audit.manual_review_approved_at = datetime.now().isoformat()
    state.save(settings.output_dir)

    logger.success(f"Audit freigegeben für Run: {run_id}")
    logger.info("Weiter mit: python pipeline.py resume " + run_id + " --stages 5,6")


@app.command()
def redesign(
    run_id: str = typer.Argument(..., help="Run-ID aus 'list-runs'"),
    feedback: str = typer.Option("", "--feedback", "-f", help="Feedback zur letzten Iteration"),
    variance: int = typer.Option(5, "--variance", min=1, max=10, help="Design-Variance (1=konservativ, 10=experimentell)"),
    motion: int = typer.Option(3, "--motion", min=1, max=10, help="Motion-Intensität (1=kein, 10=viel)"),
    density: int = typer.Option(5, "--density", min=1, max=10, help="Visual-Density (1=luftig, 10=dicht)"),
    style: str = typer.Option("auto", "--style", help="Style-Direction: auto, modern-corporate, minimal, bold, ..."),
    output_dir: Optional[Path] = typer.Option(None, "--output-dir"),
) -> None:
    """Neue Redesign-Iteration starten (mit optionalem Feedback + Taste-Dials)."""
    settings = get_settings()
    if output_dir:
        settings.output_dir = output_dir

    try:
        state = RunState.load(run_id, settings.output_dir)
    except FileNotFoundError:
        logger.error(f"Run '{run_id}' nicht gefunden.")
        raise typer.Exit(1)

    if not state.audit.manual_review_approved:
        logger.error("Audit-Review noch nicht freigegeben. Zuerst: python pipeline.py approve " + run_id)
        raise typer.Exit(1)

    params = RedesignParams(
        design_variance=variance,
        motion_intensity=motion,
        visual_density=density,
        style_direction=style,
    )

    from stages.stage5_redesign.redesign_agent import run_redesign_iteration
    asyncio.run(run_redesign_iteration(state, settings, params, feedback))
    state.save(settings.output_dir)

    logger.success(f"Redesign-Iteration {state.redesign.current_iteration} abgeschlossen.")


@app.command(name="list-runs")
def list_runs(
    output_dir: Optional[Path] = typer.Option(None, "--output-dir"),
) -> None:
    """Alle bisherigen Pipeline-Runs auflisten."""
    settings = get_settings()
    if output_dir:
        settings.output_dir = output_dir

    out = settings.output_dir
    if not out.exists():
        logger.info("Noch keine Runs vorhanden.")
        return

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Run-ID")
    table.add_column("URL")
    table.add_column("Gestartet")
    table.add_column("S1")
    table.add_column("S2")
    table.add_column("S3 Imitat")
    table.add_column("S4 Audit")
    table.add_column("S5 Redesign")
    table.add_column("S6 Paket")

    def _s(status) -> str:
        return {"done": "✅", "failed": "❌", "skipped": "⏭", "pending": "⏸", "running": "🔄"}.get(status, "?")

    for run_dir in sorted(out.iterdir(), reverse=True):
        state_file = run_dir / "run_state.json"
        if not state_file.exists():
            continue
        try:
            s = RunState.model_validate_json(state_file.read_text(encoding="utf-8"))
            review = "✅" if s.audit.manual_review_approved else "⏳"
            table.add_row(
                s.run_id,
                s.url,
                s.started_at.strftime("%Y-%m-%d %H:%M"),
                _s(s.scraper.status),
                _s(s.vault.status),
                _s(s.imitate.status),
                f"{_s(s.audit.status)} {review}",
                _s(s.redesign.status),
                _s(s.package.status),
            )
        except Exception:
            continue

    logger.console.print(table)


if __name__ == "__main__":
    app()
