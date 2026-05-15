"""Stage 4 Audit agent — 4 categories (accessibility, seo, ux_ui, usability) + manual review."""
import asyncio
import json
from datetime import date, datetime
from pathlib import Path

import anthropic
from jinja2 import Environment, FileSystemLoader

from shared import logger
from shared.run_state import RunState, Status
from stages.stage1_scraper.scraper import load_scraped_data
from stages.stage1_scraper.models import ScrapedData
from stages.stage4_audit.tools import AUDIT_TOOLS

_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
_ALL_CATEGORIES = ["accessibility", "seo", "ux_ui", "usability"]
_CATEGORY_LABEL = {
    "accessibility": "Barrierefreiheit",
    "seo": "SEO",
    "ux_ui": "UX/UI",
    "usability": "Usability & Responsiveness",
}


class AuditAgent:
    def __init__(self, client: anthropic.Anthropic, model: str):
        self.client = client
        self.model = model
        self.findings: list[dict] = []
        self.scores: dict[str, int] = {}
        self.report_meta: dict = {}

    def _handle_tool(self, name: str, inp: dict) -> dict:
        if name == "record_finding":
            self.findings.append(inp)
            return {"ok": True, "finding_number": len(self.findings)}
        elif name == "set_category_score":
            self.scores[inp["category"]] = inp["score"]
            return {"ok": True}
        elif name == "generate_report":
            self.report_meta = inp
            return {"ok": True, "message": "Report wird generiert."}
        return {"ok": False, "error": f"Unbekanntes Tool: {name}"}

    def _run_sync(self, system_prompt: str, user_prompt: str) -> dict:
        messages = [{"role": "user", "content": user_prompt}]

        for _ in range(12):
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system_prompt,
                tools=AUDIT_TOOLS,
                messages=messages,
            )

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = self._handle_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result),
                    })

            if response.stop_reason == "end_turn" or not tool_results:
                break

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

            if "generate_report" in str(response.content):
                break

        return {
            "findings": self.findings,
            "scores": self.scores,
            "meta": self.report_meta,
        }

    async def run(self, system_prompt: str, user_prompt: str) -> dict:
        return await asyncio.to_thread(self._run_sync, system_prompt, user_prompt)


def _build_user_prompt(data: ScrapedData, prompts_dir: Path) -> str:
    env = Environment(loader=FileSystemLoader(str(prompts_dir)))
    template = env.get_template("audit_user.md.j2")
    return template.render(
        url=data.url,
        domain=data.domain,
        scraped_date=data.scraped_at[:10],
        pages_crawled=data.pages_crawled,
        meta=data.meta,
        content=data.content,
        colors=data.colors,
        typography=data.typography,
        icons=data.icons,
        sitemap=data.sitemap,
        spacing=data.spacing_tokens,
        motion=data.motion_tokens,
        components=data.components,
        tech={
            "external_scripts": data.content.external_scripts,
            "external_stylesheets": data.content.external_stylesheets,
            "lazy_images": data.content.lazy_images,
            "has_impressum": data.content.has_impressum,
            "has_privacy": data.content.has_privacy,
            "frameworks": data.raw_assets.frameworks_detected,
            "mobile_screenshot": data.mobile_screenshot_path,
            "tablet_screenshot": data.tablet_screenshot_path,
        },
    )


def _render_report_markdown(data: ScrapedData, result: dict) -> str:
    findings = sorted(result["findings"], key=lambda f: _SEVERITY_ORDER.get(f.get("severity", "low"), 3))
    scores = result["scores"]
    meta = result.get("meta", {})

    severity_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}

    by_cat: dict[str, list] = {cat: [] for cat in _ALL_CATEGORIES}
    for f in findings:
        cat = f.get("category", "ux_ui")
        by_cat.setdefault(cat, []).append(f)

    findings_sections = ""
    for cat in _ALL_CATEGORIES:
        cat_findings = by_cat.get(cat, [])
        if not cat_findings:
            continue
        score = scores.get(cat, "—")
        label = _CATEGORY_LABEL.get(cat, cat)
        findings_sections += f"\n## {label} (Score: {score}/100)\n\n"
        for f in cat_findings:
            emoji = severity_emoji.get(f.get("severity", "low"), "⚪")
            wcag = f" · WCAG {f['wcag_criterion']}" if f.get("wcag_criterion") else ""
            findings_sections += f"### {emoji} {f['title']}\n\n"
            findings_sections += f"**Schweregrad:** {f.get('severity', '—').upper()}{wcag}\n\n"
            findings_sections += f"{f.get('description', '')}\n\n"
            if f.get("current_value"):
                findings_sections += f"**Aktuell:** `{f['current_value']}`\n\n"
            if f.get("recommended_value"):
                findings_sections += f"**Empfehlung:** `{f['recommended_value']}`\n\n"
            if f.get("impact"):
                findings_sections += f"**Impact:** {f['impact']}\n\n"
            findings_sections += "---\n\n"

    score_table = "\n".join(
        f"| {_CATEGORY_LABEL.get(k, k)} | {v}/100 |"
        for k, v in scores.items()
    )

    critical_count = sum(1 for f in findings if f.get("severity") == "critical")
    high_count = sum(1 for f in findings if f.get("severity") == "high")

    return f"""---
title: Audit-Report
type: client-audit-section
domain: {data.domain}
audit_date: {date.today().isoformat()}
score_accessibility: {scores.get("accessibility", "null")}
score_seo: {scores.get("seo", "null")}
score_ux_ui: {scores.get("ux_ui", "null")}
score_usability: {scores.get("usability", "null")}
findings_total: {len(findings)}
findings_critical: {critical_count}
findings_high: {high_count}
tags: [audit, akquipe]
---

# Website Audit Report
## {data.domain}

**Erstellt:** {date.today().strftime("%d.%m.%Y")} · **Analysiert:** {data.url}

---

## Executive Summary

{meta.get("executive_summary", "Kein Summary verfügbar.")}

**Top-Priorität:** {meta.get("top_priority", "—")}

---

## Ergebnis-Übersicht

| Kategorie | Score |
|---|---|
{score_table}

**Befunde gesamt:** {len(findings)} ({critical_count} kritisch, {high_count} hoch)

---
{findings_sections}

---

*Audit erstellt mit akquipe · {date.today().strftime("%d.%m.%Y")}*
"""


async def run_audit(state: RunState, settings) -> RunState:
    state.audit.status = Status.RUNNING

    try:
        data = load_scraped_data(state, settings.output_dir)

        prompts_dir = Path("config/prompts")
        system_prompt = (prompts_dir / "audit_system.md").read_text(encoding="utf-8")
        user_prompt = _build_user_prompt(data, prompts_dir)

        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        agent = AuditAgent(client=client, model=settings.audit_model)

        logger.info(f"Starte Audit-Agent ({settings.audit_model})...")
        result = await agent.run(system_prompt, user_prompt)

        audit_md = _render_report_markdown(data, result)

        run_dir = state.run_dir(settings.output_dir)
        audit_dir = run_dir / "audit"
        audit_dir.mkdir(parents=True, exist_ok=True)

        md_path = audit_dir / "audit_report.md"
        md_path.write_text(audit_md, encoding="utf-8")

        state.audit.status = Status.DONE
        state.audit.report_md_path = str(md_path)
        state.audit.scores = result["scores"]
        state.audit.findings_count = {
            cat: sum(1 for f in result["findings"] if f.get("category") == cat)
            for cat in _ALL_CATEGORIES
        }

        logger.success(f"Audit abgeschlossen — {len(result['findings'])} Befunde | Scores: {result['scores']}")

        from stages.stage2_vault.vault_writer import update_vault_audit_report
        update_vault_audit_report(state, settings, audit_md)

        from stages.stage3_audit.report_renderer import render_pdf
        pdf_path = await render_pdf(md_path, audit_dir)
        if pdf_path:
            state.audit.report_pdf_path = str(pdf_path)

    except Exception as e:
        state.audit.status = Status.FAILED
        state.audit.error = str(e)
        logger.error(f"Audit-Agent fehlgeschlagen: {e}")
        raise

    return state
