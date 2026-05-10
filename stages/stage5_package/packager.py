import shutil
import zipfile
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from shared import logger
from shared.run_state import RunState, Status
from stages.stage5_package.pricing import calculate_price, format_pricing_md


def run_packager(state: RunState, settings) -> RunState:
    state.package.status = Status.RUNNING

    try:
        run_dir = state.run_dir(settings.output_dir)
        package_dir = run_dir / "package"
        package_dir.mkdir(parents=True, exist_ok=True)

        price = calculate_price(state, settings.freelancer_day_rate)
        state.package.pricing_eur = price

        # 1. Pricing Markdown
        pricing_md = format_pricing_md(state, price, settings.freelancer_day_rate)
        pricing_path = package_dir / "04_Preisvorschlag.md"
        pricing_path.write_text(pricing_md, encoding="utf-8")

        # 2. Cover letter
        cover_path = _write_cover_letter(state, package_dir)

        # 3. Zip reconstructed site (if exists)
        site_zip: Path | None = None
        if state.reconstruct.project_path:
            site_zip = _zip_directory(
                Path(state.reconstruct.project_path),
                package_dir / "03_Rekonstruierte_Website.zip",
            )

        # 4. Bundle everything into final ZIP
        today = date.today().strftime("%Y%m%d")
        zip_name = f"{state.domain}_{today}_proposal.zip"
        zip_path = package_dir / zip_name

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # Audit Report PDF (or MD as fallback)
            if state.audit.report_pdf_path and Path(state.audit.report_pdf_path).exists():
                zf.write(state.audit.report_pdf_path, "01_Audit_Report.pdf")
            elif state.audit.report_md_path and Path(state.audit.report_md_path).exists():
                zf.write(state.audit.report_md_path, "01_Audit_Report.md")

            if cover_path and cover_path.exists():
                zf.write(cover_path, f"02_Anschreiben.md")

            if site_zip and site_zip.exists():
                zf.write(site_zip, "03_Rekonstruierte_Website.zip")

            if pricing_path.exists():
                zf.write(pricing_path, "04_Preisvorschlag.md")

        state.package.status = Status.DONE
        state.package.zip_path = str(zip_path)
        logger.success(f"Paket erstellt: {zip_path} ({zip_path.stat().st_size // 1024} KB)")

    except Exception as e:
        state.package.status = Status.FAILED
        state.package.error = str(e)
        logger.error(f"Packager fehlgeschlagen: {e}")
        raise

    return state


def _write_cover_letter(state: RunState, package_dir: Path) -> Path:
    env = Environment(loader=FileSystemLoader("config/prompts"))
    template = env.get_template("cover_letter.md.j2")

    content = template.render(
        client_domain=state.domain,
        url=state.url,
        date=date.today().strftime("%d.%m.%Y"),
        scores=state.audit.scores,
        top_priority="Bitte Audit-Report für Details beachten.",
    )

    path = package_dir / "02_Anschreiben.md"
    path.write_text(content, encoding="utf-8")
    return path


def _zip_directory(source_dir: Path, zip_path: Path) -> Path:
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in source_dir.rglob("*"):
            if file.is_file():
                # Skip node_modules and .next
                parts = file.parts
                if "node_modules" in parts or ".next" in parts:
                    continue
                zf.write(file, file.relative_to(source_dir))
    return zip_path
