import asyncio
import subprocess
from pathlib import Path

from shared import logger


async def render_pdf(md_path: Path, output_dir: Path) -> Path | None:
    """Convert Markdown to PDF via npx md-to-pdf."""
    pdf_path = output_dir / md_path.with_suffix(".pdf").name

    try:
        result = await asyncio.create_subprocess_exec(
            "npx", "md-to-pdf",
            str(md_path),
            "--dest", str(pdf_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(result.communicate(), timeout=60)

        if result.returncode == 0 and pdf_path.exists():
            logger.success(f"PDF generiert: {pdf_path}")
            return pdf_path
        else:
            logger.warning(f"PDF-Generierung fehlgeschlagen (npx md-to-pdf): {stderr.decode()[:200]}")
            return _render_pdf_fallback(md_path, output_dir)

    except (FileNotFoundError, asyncio.TimeoutError) as e:
        logger.warning(f"npx md-to-pdf nicht verfügbar ({e}), versuche Fallback...")
        return _render_pdf_fallback(md_path, output_dir)


def _render_pdf_fallback(md_path: Path, output_dir: Path) -> Path | None:
    """Fallback: write a simple HTML file that can be printed to PDF."""
    html_path = output_dir / md_path.with_suffix(".html").name
    try:
        import re
        content = md_path.read_text(encoding="utf-8")

        # Strip frontmatter
        if content.startswith("---"):
            end = content.find("---", 3)
            if end > 0:
                content = content[end + 3:].lstrip()

        # Very basic markdown to HTML
        lines = content.split("\n")
        html_lines = []
        for line in lines:
            if line.startswith("### "):
                html_lines.append(f"<h3>{line[4:]}</h3>")
            elif line.startswith("## "):
                html_lines.append(f"<h2>{line[3:]}</h2>")
            elif line.startswith("# "):
                html_lines.append(f"<h1>{line[2:]}</h1>")
            elif line.startswith("---"):
                html_lines.append("<hr>")
            elif line.startswith("| "):
                html_lines.append(f"<tr><td>{'</td><td>'.join(c.strip() for c in line.split('|')[1:-1])}</td></tr>")
            elif line.startswith("**") and line.endswith("**"):
                html_lines.append(f"<strong>{line[2:-2]}</strong><br>")
            elif line.strip():
                html_lines.append(f"<p>{line}</p>")

        html = f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<title>Audit Report</title>
<style>
  body {{ font-family: Arial, sans-serif; max-width: 900px; margin: 40px auto; color: #333; line-height: 1.6; }}
  h1 {{ color: #1a1a2e; border-bottom: 3px solid #1a1a2e; }}
  h2 {{ color: #16213e; border-bottom: 1px solid #ddd; }}
  h3 {{ color: #0f3460; }}
  table {{ border-collapse: collapse; width: 100%; }}
  td, th {{ border: 1px solid #ddd; padding: 8px 12px; }}
  hr {{ border: none; border-top: 1px solid #ddd; }}
  code {{ background: #f4f4f4; padding: 2px 6px; border-radius: 3px; }}
</style>
</head>
<body>
{''.join(html_lines)}
<p style="color:#999;font-size:12px;margin-top:40px">Audit erstellt mit akquipe — Zum PDF drucken: Datei → Drucken → Als PDF speichern</p>
</body>
</html>"""

        html_path.write_text(html, encoding="utf-8")
        logger.info(f"HTML-Report gespeichert (als PDF drucken): {html_path}")
        return html_path

    except Exception as e:
        logger.error(f"Auch HTML-Fallback fehlgeschlagen: {e}")
        return None
