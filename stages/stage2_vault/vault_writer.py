import shutil
from pathlib import Path

from shared import logger
from shared.run_state import RunState, Status
from shared.utils import safe_filename
from stages.stage1_scraper.scraper import load_scraped_data
from stages.stage2_vault.note_builders import (
    colors as nb_colors,
    hierarchy as nb_hierarchy,
    icons as nb_icons,
    overview as nb_overview,
    screenshots as nb_screenshots,
    typography as nb_typography,
    userflow as nb_userflow,
)
from stages.stage2_vault.note_builders import design_system as nb_design_system


def run_vault_writer(state: RunState, settings) -> RunState:
    state.vault.status = Status.RUNNING

    try:
        data = load_scraped_data(state, settings.output_dir)
        vault_root = settings.effective_vault_path()
        client_folder = vault_root / "akquipe" / safe_filename(state.domain)
        assets_screenshots = client_folder / "assets" / "screenshots"
        assets_icons = client_folder / "assets" / "icons"

        client_folder.mkdir(parents=True, exist_ok=True)
        assets_screenshots.mkdir(parents=True, exist_ok=True)
        assets_icons.mkdir(parents=True, exist_ok=True)

        # Copy screenshots into vault
        if state.scraper.screenshots_dir:
            src_screenshots = Path(state.scraper.screenshots_dir)
            if src_screenshots.exists():
                for img in src_screenshots.iterdir():
                    if img.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                        shutil.copy2(img, assets_screenshots / img.name)

        # Copy icon SVGs into vault
        run_dir = state.run_dir(settings.output_dir)
        icons_src = run_dir / "scraped" / "assets" / "icons"
        if icons_src.exists():
            for svg in icons_src.iterdir():
                if svg.suffix.lower() == ".svg":
                    shutil.copy2(svg, assets_icons / svg.name)

        notes = {
            "_Overview.md": nb_overview.build_overview(data, state.run_id),
            "Colors.md": nb_colors.build_colors(data),
            "Typography.md": nb_typography.build_typography(data),
            "Icons.md": nb_icons.build_icons(data),
            "Page-Hierarchy.md": nb_hierarchy.build_hierarchy(data),
            "User-Flow.md": nb_userflow.build_userflow(data),
            "Screenshots.md": nb_screenshots.build_screenshots(data, assets_screenshots),
            "DESIGN.md": nb_design_system.build_design_system(data),
            "Audit-Report.md": "---\ntitle: Audit-Report\ntype: client-audit-section\nstatus: pending\n---\n\n# Audit-Report\n\n> Wird nach Stage 4 automatisch befüllt.\n",
        }

        for filename, content in notes.items():
            path = client_folder / filename
            path.write_text(content, encoding="utf-8")
            logger.dim(f"  → {filename} geschrieben")

        state.vault.status = Status.DONE
        state.vault.folder_path = str(client_folder)
        logger.success(f"Vault-Notes erstellt: {client_folder}")

    except Exception as e:
        state.vault.status = Status.FAILED
        state.vault.error = str(e)
        logger.error(f"Vault-Writer fehlgeschlagen: {e}")
        raise

    return state


def update_vault_audit_report(state: RunState, settings, audit_md: str) -> None:
    if not state.vault.folder_path:
        return
    report_path = Path(state.vault.folder_path) / "Audit-Report.md"
    report_path.write_text(audit_md, encoding="utf-8")

    # Update frontmatter scores in _Overview.md
    overview_path = Path(state.vault.folder_path) / "_Overview.md"
    if overview_path.exists():
        text = overview_path.read_text(encoding="utf-8")
        for key, val in state.audit.scores.items():
            text = text.replace(f"audit_score_{key}: null", f"audit_score_{key}: {val}")
        text = text.replace("status: scraped", "status: audit-complete")
        text = text.replace("audit-pending", "audit-complete")
        overview_path.write_text(text, encoding="utf-8")
