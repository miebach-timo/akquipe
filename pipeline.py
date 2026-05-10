"""akquipe -- UX/UI Freelancer Akquise-Pipeline"""

import asyncio
import sys
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
from shared.run_state import RunState, Status
from shared.utils import domain_from_url, run_id_from_url

app = typer.Typer(
    name="akquipe",
    help="UX/UI Freelancer Pipeline: Scrape -> Vault -> Audit -> Rebuild -> Package",
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
    stages: str = typer.Option("1,2,3,4,5", "--stages", "-s", help="Kommaseparierte Stage-Nummern"),
    run_id: Optional[str] = typer.Option(None, "--run-id", help="Bestehenden Run fortsetzen"),
    skip_reconstruct: bool = typer.Option(False, "--skip-reconstruct", help="Stage 4 überspringen"),
    vault_path: Optional[Path] = typer.Option(None, "--vault-path", help="Obsidian Vault-Pfad"),
    output_dir: Optional[Path] = typer.Option(None, "--output-dir", help="Ausgabeverzeichnis"),
) -> None:
    """Vollständige Pipeline für eine Website starten."""
    settings = get_settings()

    if output_dir:
        settings.output_dir = output_dir
    if vault_path:
        settings.vault_path = vault_path
    if skip_reconstruct:
        stages_str = stages.replace("4,", "").replace(",4", "").replace("4", "")
        stages = stages_str or "1,2,3,5"

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

    logger.console.rule(f"[bold cyan]akquipe[/bold cyan] — {url}")
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
            logger.stage(2, "Obsidian Vault befüllen")
            from stages.stage2_vault.vault_writer import run_vault_writer
            state = run_vault_writer(state, settings)
            state.save(settings.output_dir)

    if 3 in active_stages and state.audit.status != Status.DONE:
        if state.scraper.status != Status.DONE:
            logger.warning("Stage 3 übersprungen — Stage 1 nicht abgeschlossen.")
        else:
            logger.stage(3, "KI-Audit durchführen")
            from stages.stage3_audit.agent import run_audit
            state = await run_audit(state, settings)
            state.save(settings.output_dir)

    if 4 in active_stages and state.reconstruct.status != Status.DONE:
        if state.scraper.status != Status.DONE:
            logger.warning("Stage 4 übersprungen — Stage 1 nicht abgeschlossen.")
        else:
            logger.stage(4, "Website rekonstruieren")
            from stages.stage4_reconstruct.scaffolder import run_reconstruct
            state = await run_reconstruct(state, settings)
            state.save(settings.output_dir)

    if 5 in active_stages and state.package.status != Status.DONE:
        logger.stage(5, "Kundenpaket schnüren")
        from stages.stage5_package.packager import run_packager
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
    scores = state.audit.scores
    score_str = f"Accessibility: {scores.get('accessibility', '—')} | SEO: {scores.get('seo', '—')} | UX/UI: {scores.get('ux_ui', '—')}"
    table.add_row("3 Audit", _icon(state.audit.status), score_str)
    table.add_row("4 Rekonstruktion", _icon(state.reconstruct.status), state.reconstruct.project_path or "—")
    table.add_row("5 Paket", _icon(state.package.status), state.package.zip_path or "—")

    logger.console.print(table)

    if state.package.zip_path:
        logger.success(f"Paket bereit: {state.package.zip_path}")
    if state.package.pricing_eur:
        logger.info(f"Preisvorschlag: {state.package.pricing_eur:,.0f} EUR")


@app.command()
def resume(
    run_id: str = typer.Argument(..., help="Run-ID aus 'list-runs'"),
    stages: str = typer.Option("1,2,3,4,5", "--stages", "-s"),
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
    table.add_column("Scraper")
    table.add_column("Vault")
    table.add_column("Audit")
    table.add_column("Rekonstruktion")
    table.add_column("Paket")

    def _s(status) -> str:
        return {"done": "✅", "failed": "❌", "skipped": "⏭", "pending": "⏸", "running": "🔄"}.get(status, "?")

    for run_dir in sorted(out.iterdir(), reverse=True):
        state_file = run_dir / "run_state.json"
        if not state_file.exists():
            continue
        try:
            s = RunState.model_validate_json(state_file.read_text(encoding="utf-8"))
            table.add_row(
                s.run_id,
                s.url,
                s.started_at.strftime("%Y-%m-%d %H:%M"),
                _s(s.scraper.status),
                _s(s.vault.status),
                _s(s.audit.status),
                _s(s.reconstruct.status),
                _s(s.package.status),
            )
        except Exception:
            continue

    logger.console.print(table)


if __name__ == "__main__":
    app()
