"""Stage 6: Package — bundle audit, imitate/redesign and cover letter into a deliverable ZIP."""
import shutil
import zipfile
from datetime import date
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from shared import logger
from shared.run_state import RunState, Status
from stages.stage6_package.pricing import calculate_price, format_pricing_md


def run_packager(state: RunState, settings) -> RunState:
    state.package.status = Status.RUNNING

    try:
        run_dir = state.run_dir(settings.output_dir)
        package_dir = run_dir / "package"
        package_dir.mkdir(parents=True, exist_ok=True)

        price = calculate_price(state, settings.freelancer_day_rate)
        state.package.pricing_eur = price

        pricing_md = format_pricing_md(state, price, settings.freelancer_day_rate)
        pricing_path = package_dir / "04_Preisvorschlag.md"
        pricing_path.write_text(pricing_md, encoding="utf-8")

        cover_path = _write_cover_letter(state, package_dir)

        # Changelog: Vorher/Nachher
        changelog_path = _write_changelog(state, package_dir)

        # Zip redesign (prefer redesign over imitate)
        site_zip: Path | None = None
        redesign_path = state.redesign.project_path
        imitate_path = state.imitate.project_path

        if redesign_path and Path(redesign_path).exists():
            site_zip = _zip_directory(
                Path(redesign_path),
                package_dir / "03_Redesign_Website.zip",
            )
        elif imitate_path and Path(imitate_path).exists():
            site_zip = _zip_directory(
                Path(imitate_path),
                package_dir / "03_Imitat_Website.zip",
            )
        elif state.reconstruct.project_path and Path(state.reconstruct.project_path).exists():
            site_zip = _zip_directory(
                Path(state.reconstruct.project_path),
                package_dir / "03_Rekonstruierte_Website.zip",
            )

        today = date.today().strftime("%Y%m%d")
        zip_name = f"{state.domain}_{today}_proposal.zip"
        zip_path = package_dir / zip_name

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            if state.audit.report_pdf_path and Path(state.audit.report_pdf_path).exists():
                zf.write(state.audit.report_pdf_path, "01_Audit_Report.pdf")
            elif state.audit.report_md_path and Path(state.audit.report_md_path).exists():
                zf.write(state.audit.report_md_path, "01_Audit_Report.md")

            if cover_path and cover_path.exists():
                zf.write(cover_path, "02_Anschreiben.md")

            if site_zip and site_zip.exists():
                zf.write(site_zip, site_zip.name)

            if pricing_path.exists():
                zf.write(pricing_path, "04_Preisvorschlag.md")

            if changelog_path and changelog_path.exists():
                zf.write(changelog_path, "05_Changelog.md")

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

    audit_findings = sum(state.audit.findings_count.values())
    scores = state.audit.scores

    # Build a specific finding hook for the cover letter
    worst_score_key = min(scores, key=lambda k: scores[k]) if scores else None
    worst_score_label = {
        "accessibility": "Barrierefreiheit",
        "seo": "SEO",
        "ux_ui": "UX/UI",
        "usability": "Usability & Responsiveness",
    }.get(worst_score_key, "Design") if worst_score_key else "Design"

    content = template.render(
        client_domain=state.domain,
        url=state.url,
        date=date.today().strftime("%d.%m.%Y"),
        scores=scores,
        findings_total=audit_findings,
        worst_category=worst_score_label,
        worst_score=scores.get(worst_score_key, "—") if worst_score_key else "—",
        has_redesign=state.redesign.status.value == "done",
        has_imitate=state.imitate.status.value == "done",
        top_priority="Bitte Audit-Report für Details beachten.",
    )

    path = package_dir / "02_Anschreiben.md"
    path.write_text(content, encoding="utf-8")
    return path


def _write_changelog(state: RunState, package_dir: Path) -> Path | None:
    if not state.audit.report_md_path:
        return None

    lines = [
        f"# Changelog — {state.domain}",
        "",
        f"**Erstellt:** {date.today().strftime('%d.%m.%Y')}",
        "",
        "---",
        "",
        "## Vorher / Nachher (Audit-Scores)",
        "",
        "| Kategorie | Original-Score | Ziel nach Redesign |",
        "|---|---|---|",
    ]

    labels = {
        "accessibility": "Barrierefreiheit",
        "seo": "SEO",
        "ux_ui": "UX/UI",
        "usability": "Usability",
    }
    for key, label in labels.items():
        score = state.audit.scores.get(key, "—")
        target = min(int(score) + 25, 95) if isinstance(score, int) else "—"
        lines.append(f"| {label} | {score}/100 | {target}/100 |")

    lines += [
        "",
        "---",
        "",
        "## Durchgeführte Verbesserungen",
        "",
        "Basierend auf den Audit-Befunden wurden folgende Bereiche verbessert:",
        "",
    ]

    if state.audit.findings_count:
        total = sum(state.audit.findings_count.values())
        for cat, label in labels.items():
            count = state.audit.findings_count.get(cat, 0)
            if count > 0:
                lines.append(f"- **{label}**: {count} Befunde adressiert")

    if state.redesign.iterations:
        lines += [
            "",
            f"## Redesign-Iterationen ({len(state.redesign.iterations)}x)",
            "",
        ]
        for it in state.redesign.iterations:
            feedback = f" · Feedback: {it.user_feedback}" if it.user_feedback else ""
            lines.append(
                f"- **Iteration {it.iteration}** — Variance: {it.params.design_variance}/10, "
                f"Motion: {it.params.motion_intensity}/10, Density: {it.params.visual_density}/10"
                f"{feedback}"
            )

    changelog_md = "\n".join(lines)
    path = package_dir / "05_Changelog.md"
    path.write_text(changelog_md, encoding="utf-8")
    return path


def _zip_directory(source_dir: Path, zip_path: Path) -> Path:
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in source_dir.rglob("*"):
            if file.is_file():
                parts = file.parts
                if "node_modules" in parts or ".next" in parts:
                    continue
                zf.write(file, file.relative_to(source_dir))
    return zip_path
