"""akquipe Dashboard — Streamlit UI"""

import json
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import streamlit as st

from shared.client_meta import (
    AKQUISE_STATI,
    STATUS_COLORS,
    ClientMeta,
    load_client_meta,
    save_client_meta,
)
from shared.run_state import RunState, Status

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="akquipe",
    page_icon="A",
    layout="wide",
    initial_sidebar_state="expanded",
)

OUTPUT_DIR = Path("output")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _status_badge(label: str, color: str) -> str:
    return f'<span style="background:{color};color:#fff;padding:2px 10px;border-radius:12px;font-size:12px;font-weight:600">{label}</span>'


def _stage_badge(status: Status) -> str:
    cfg = {
        Status.DONE:    ("#22c55e", "Fertig"),
        Status.FAILED:  ("#ef4444", "Fehler"),
        Status.RUNNING: ("#f97316", "Lauft"),
        Status.SKIPPED: ("#9ca3af", "Ubersprungen"),
        Status.PENDING: ("#d1d5db", "Ausstehend"),
    }
    color, text = cfg.get(status, ("#d1d5db", status.value))
    return _status_badge(text, color)


def _score_color(score: int) -> str:
    if score >= 80:
        return "#22c55e"
    if score >= 60:
        return "#f97316"
    return "#ef4444"


def _load_all_runs() -> list[tuple[RunState, ClientMeta]]:
    runs = []
    if not OUTPUT_DIR.exists():
        return runs
    for d in sorted(OUTPUT_DIR.iterdir(), reverse=True):
        state_file = d / "run_state.json"
        if not state_file.exists():
            continue
        try:
            state = RunState.model_validate_json(state_file.read_text(encoding="utf-8"))
            meta = load_client_meta(d)
            runs.append((state, meta))
        except Exception:
            continue
    return runs


def _load_scraped_data(state: RunState) -> Optional[dict]:
    if not state.scraper.data_path:
        return None
    p = Path(state.scraper.data_path)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return None


def _open_folder(path: str) -> None:
    try:
        subprocess.Popen(["explorer", path])
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

def render_sidebar(runs: list[tuple[RunState, ClientMeta]]) -> Optional[str]:
    with st.sidebar:
        st.markdown("## akquipe")
        st.markdown("---")

        search = st.text_input("Suche", placeholder="Domain filtern...")

        filtered = [
            (s, m) for s, m in runs
            if not search or search.lower() in s.domain.lower()
        ]

        if not filtered:
            st.info("Noch keine Projekte.")
            return None

        st.markdown(f"**{len(filtered)} Projekte**")
        st.markdown("")

        selected_id = st.session_state.get("selected_run_id")

        for state, meta in filtered:
            status_color = STATUS_COLORS.get(meta.akquise_status, "#9ca3af")
            is_selected = state.run_id == selected_id

            label = f"**{state.domain}**  \n{state.started_at.strftime('%d.%m.%Y')}"
            badge_html = _status_badge(meta.akquise_status, status_color)

            container_style = (
                "border-left:3px solid #3b82f6;padding-left:8px;"
                if is_selected else
                "border-left:3px solid transparent;padding-left:8px;"
            )

            with st.container():
                st.markdown(f'<div style="{container_style}">', unsafe_allow_html=True)
                col_l, col_r = st.columns([3, 1])
                with col_l:
                    if st.button(label, key=f"btn_{state.run_id}", use_container_width=True):
                        st.session_state["selected_run_id"] = state.run_id
                        st.rerun()
                with col_r:
                    st.markdown(f"<br>{badge_html}", unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)

        return st.session_state.get("selected_run_id")


# ---------------------------------------------------------------------------
# Tab 1 — Uebersicht
# ---------------------------------------------------------------------------

def render_tab_overview(state: RunState, scraped: Optional[dict]) -> None:
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown(f"### {state.domain}")
        st.markdown(f"[{state.url}]({state.url})")
        if scraped and scraped.get("meta", {}).get("title"):
            st.caption(scraped["meta"]["title"])

    with col2:
        st.markdown(f"**Gestartet:** {state.started_at.strftime('%d.%m.%Y %H:%M')}")
        if scraped:
            st.markdown(f"**Seiten gecrawlt:** {scraped.get('pages_crawled', '—')}")

    st.markdown("---")

    # Pipeline Status
    st.markdown("**Pipeline-Status**")
    cols = st.columns(5)
    stages = [
        ("Scraper", state.scraper.status),
        ("Vault", state.vault.status),
        ("Audit", state.audit.status),
        ("Redesign", state.reconstruct.status),
        ("Paket", state.package.status),
    ]
    for col, (name, status) in zip(cols, stages):
        with col:
            st.markdown(f"<center><small>{name}</small><br>{_stage_badge(status)}</center>", unsafe_allow_html=True)

    st.markdown("")

    # Audit Scores
    if state.audit.scores:
        st.markdown("**Audit-Scores**")
        score_cols = st.columns(3)
        labels = {"accessibility": "Barrierefreiheit", "seo": "SEO", "ux_ui": "UX/UI"}
        for col, (key, label) in zip(score_cols, labels.items()):
            score = state.audit.scores.get(key, 0)
            with col:
                color = _score_color(score)
                st.markdown(
                    f'<div style="text-align:center">'
                    f'<div style="font-size:36px;font-weight:700;color:{color}">{score}</div>'
                    f'<div style="font-size:12px;color:#6b7280">{label}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        st.markdown("")

    # Farbpalette
    if scraped and scraped.get("colors", {}).get("palette"):
        st.markdown("**Farbpalette**")
        palette = scraped["colors"]["palette"][:10]
        color_cols = st.columns(len(palette))
        for col, c in zip(color_cols, palette):
            with col:
                st.markdown(
                    f'<div style="width:100%;height:40px;background:{c["hex"]};border-radius:6px;border:1px solid #e5e7eb"></div>'
                    f'<div style="font-size:10px;text-align:center;color:#6b7280;margin-top:2px">{c["hex"]}</div>',
                    unsafe_allow_html=True,
                )
        st.markdown("")

    # Screenshots
    if scraped and scraped.get("screenshots"):
        st.markdown("**Screenshots**")
        shots = [p for p in scraped["screenshots"] if Path(p).exists()]
        if shots:
            shot_cols = st.columns(min(len(shots), 3))
            for col, path in zip(shot_cols, shots[:3]):
                with col:
                    try:
                        st.image(path, use_container_width=True, caption=Path(path).stem)
                    except Exception:
                        pass
        else:
            st.caption("Screenshots noch nicht verfugbar.")


# ---------------------------------------------------------------------------
# Tab 2 — Akquise-Tracking
# ---------------------------------------------------------------------------

def render_tab_akquise(state: RunState, meta: ClientMeta) -> None:
    st.markdown("### Akquise-Tracking")

    run_dir = OUTPUT_DIR / state.run_id

    col1, col2 = st.columns(2)

    with col1:
        new_status = st.selectbox(
            "Akquise-Status",
            AKQUISE_STATI,
            index=AKQUISE_STATI.index(meta.akquise_status) if meta.akquise_status in AKQUISE_STATI else 0,
        )

        anfrage_datum = st.date_input(
            "Anfrage gesendet am",
            value=date.fromisoformat(meta.anfrage_datum) if meta.anfrage_datum else None,
            format="DD.MM.YYYY",
        )

        naechste_aktion = st.text_input(
            "Nachste Aktion",
            value=meta.naechste_aktion,
            placeholder="z.B. Follow-up in 1 Woche",
        )

    with col2:
        antwort_datum = st.date_input(
            "Antwort erhalten am",
            value=date.fromisoformat(meta.antwort_datum) if meta.antwort_datum else None,
            format="DD.MM.YYYY",
        )

    anfrage_notiz = st.text_area(
        "Anfrage-Notiz",
        value=meta.anfrage_notiz,
        height=120,
        placeholder="Was wurde angeboten? Wie war der erste Kontakt?",
    )

    antwort_text = st.text_area(
        "Kundenantwort",
        value=meta.antwort_text,
        height=120,
        placeholder="Was hat der Kunde geantwortet?",
    )

    if st.button("Speichern", type="primary"):
        updated = ClientMeta(
            akquise_status=new_status,
            anfrage_datum=anfrage_datum.isoformat() if anfrage_datum else None,
            anfrage_notiz=anfrage_notiz,
            antwort_datum=antwort_datum.isoformat() if antwort_datum else None,
            antwort_text=antwort_text,
            naechste_aktion=naechste_aktion,
        )
        save_client_meta(run_dir, updated)
        st.success("Gespeichert!")
        st.rerun()


# ---------------------------------------------------------------------------
# Tab 3 — Audit
# ---------------------------------------------------------------------------

def render_tab_audit(state: RunState) -> None:
    st.markdown("### Audit-Report")

    if state.audit.status != Status.DONE:
        st.info("Audit noch nicht ausgefuhrt. Stage 3 starten: `python pipeline.py run <url> --stages 3`")
        return

    # Download PDF
    col1, col2 = st.columns(2)
    with col1:
        if state.audit.report_pdf_path and Path(state.audit.report_pdf_path).exists():
            pdf_bytes = Path(state.audit.report_pdf_path).read_bytes()
            st.download_button(
                "Audit-Report herunterladen (PDF)",
                pdf_bytes,
                file_name=f"audit_{state.domain}.pdf",
                mime="application/pdf",
            )
    with col2:
        if state.audit.report_md_path and Path(state.audit.report_md_path).exists():
            md_bytes = Path(state.audit.report_md_path).read_bytes()
            st.download_button(
                "Audit-Report herunterladen (Markdown)",
                md_bytes,
                file_name=f"audit_{state.domain}.md",
                mime="text/markdown",
            )

    # Scores
    if state.audit.scores:
        st.markdown("---")
        score_cols = st.columns(3)
        labels = {"accessibility": "Barrierefreiheit", "seo": "SEO", "ux_ui": "UX/UI"}
        for col, (key, label) in zip(score_cols, labels.items()):
            score = state.audit.scores.get(key, 0)
            with col:
                st.metric(label, f"{score}/100")
                st.progress(score / 100)

    # Findings count
    if state.audit.findings_count:
        st.markdown("---")
        st.markdown("**Befunde nach Kategorie**")
        fc_cols = st.columns(3)
        for col, (key, label) in zip(fc_cols, {"accessibility": "Barrierefreiheit", "seo": "SEO", "ux_ui": "UX/UI"}.items()):
            with col:
                st.metric(label, state.audit.findings_count.get(key, 0), help="Anzahl Befunde")

    # Report Markdown
    if state.audit.report_md_path and Path(state.audit.report_md_path).exists():
        st.markdown("---")
        st.markdown("**Vollstandiger Report**")
        content = Path(state.audit.report_md_path).read_text(encoding="utf-8")
        # Strip frontmatter for display
        if content.startswith("---"):
            end = content.find("---", 3)
            if end > 0:
                content = content[end + 3:].lstrip()
        with st.expander("Report anzeigen", expanded=False):
            st.markdown(content)


# ---------------------------------------------------------------------------
# Tab 4 — Redesign
# ---------------------------------------------------------------------------

def render_tab_redesign(state: RunState) -> None:
    st.markdown("### Rekonstruierte Website")

    if state.reconstruct.status != Status.DONE:
        st.info("Rekonstruktion noch nicht ausgefuhrt. Stage 4 starten: `python pipeline.py run <url> --stages 4`")
        return

    project_path = Path(state.reconstruct.project_path) if state.reconstruct.project_path else None

    if project_path and project_path.exists():
        st.success(f"Next.js-Projekt bereit: `{project_path}`")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Ordner im Explorer offnen"):
                _open_folder(str(project_path))

        with col2:
            # Zip for download
            zip_path = OUTPUT_DIR / state.run_id / "package" / "03_Rekonstruierte_Website.zip"
            if zip_path.exists():
                st.download_button(
                    "Website-ZIP herunterladen",
                    zip_path.read_bytes(),
                    file_name=f"redesign_{state.domain}.zip",
                    mime="application/zip",
                )

        st.markdown("---")
        st.markdown("**Lokal starten:**")
        st.code(f"cd \"{project_path}\"\nnpm install\nnpm run dev", language="bash")

        # Show brand.ts if available
        brand_file = project_path / "src" / "lib" / "brand.ts"
        if brand_file.exists():
            with st.expander("Brand-Tokens anzeigen (src/lib/brand.ts)"):
                st.code(brand_file.read_text(encoding="utf-8"), language="typescript")
    else:
        st.warning("Projektordner nicht gefunden.")


# ---------------------------------------------------------------------------
# Tab 5 — Paket
# ---------------------------------------------------------------------------

def render_tab_paket(state: RunState) -> None:
    st.markdown("### Kundenpaket")

    if state.package.status != Status.DONE:
        st.info("Paket noch nicht erstellt. Stage 5 starten: `python pipeline.py run <url> --stages 5`")
        return

    # Pricing highlight
    if state.package.pricing_eur:
        st.markdown(
            f'<div style="background:#f0fdf4;border:1px solid #86efac;border-radius:8px;padding:20px;text-align:center">'
            f'<div style="font-size:14px;color:#166534;font-weight:600">Preisvorschlag</div>'
            f'<div style="font-size:40px;font-weight:700;color:#15803d">{state.package.pricing_eur:,.0f} EUR</div>'
            f'<div style="font-size:12px;color:#166534">netto, zzgl. MwSt.</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.markdown("")

    # Download ZIP
    if state.package.zip_path and Path(state.package.zip_path).exists():
        zip_bytes = Path(state.package.zip_path).read_bytes()
        zip_name = Path(state.package.zip_path).name
        st.download_button(
            "Komplettes Paket herunterladen (ZIP)",
            zip_bytes,
            file_name=zip_name,
            mime="application/zip",
            type="primary",
        )

    st.markdown("---")

    # Paket-Inhalt
    package_dir = OUTPUT_DIR / state.run_id / "package"
    st.markdown("**Paket-Inhalt:**")
    for fname, label in [
        ("01_Audit_Report.pdf", "Audit-Report (PDF)"),
        ("01_Audit_Report.md", "Audit-Report (Markdown)"),
        ("02_Anschreiben.md", "Anschreiben"),
        ("03_Rekonstruierte_Website.zip", "Website-ZIP"),
        ("04_Preisvorschlag.md", "Preisvorschlag"),
    ]:
        p = package_dir / fname
        if p.exists():
            suffix = p.suffix
            mime = "application/pdf" if suffix == ".pdf" else "application/zip" if suffix == ".zip" else "text/markdown"
            st.download_button(
                f"  {label}",
                p.read_bytes(),
                file_name=fname,
                mime=mime,
                key=f"dl_{fname}",
            )

    # Anschreiben Vorschau
    anschreiben = package_dir / "02_Anschreiben.md"
    if anschreiben.exists():
        st.markdown("---")
        with st.expander("Anschreiben-Vorschau"):
            st.markdown(anschreiben.read_text(encoding="utf-8"))

    # Preisvorschlag Vorschau
    preis = package_dir / "04_Preisvorschlag.md"
    if preis.exists():
        with st.expander("Preisvorschlag-Vorschau"):
            st.markdown(preis.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Hauptansicht — kein Projekt gewahlt
# ---------------------------------------------------------------------------

def render_empty_state(runs: list) -> None:
    st.markdown("## Willkommen bei akquipe")
    st.markdown("Deine UX/UI Akquise-Pipeline.")
    st.markdown("---")

    if not runs:
        st.info("Noch keine Projekte vorhanden. Starte deinen ersten Run:")
        st.code("python pipeline.py run https://kundenwebsite.de", language="bash")
    else:
        st.markdown(f"**{len(runs)} Projekte** in der Sidebar — klicke ein Projekt an.")

        # Mini-Übersicht aller Projekte
        st.markdown("---")
        st.markdown("### Alle Projekte")
        for state, meta in runs[:20]:
            sc = STATUS_COLORS.get(meta.akquise_status, "#9ca3af")
            badge = _status_badge(meta.akquise_status, sc)
            scores = state.audit.scores
            score_str = ""
            if scores:
                score_str = f" · A:{scores.get('accessibility','—')} S:{scores.get('seo','—')} UX:{scores.get('ux_ui','—')}"
            st.markdown(
                f"{badge} &nbsp; **{state.domain}** &nbsp; "
                f"<span style='color:#6b7280;font-size:13px'>{state.started_at.strftime('%d.%m.%Y')}{score_str}</span>",
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    runs = _load_all_runs()
    selected_id = render_sidebar(runs)

    if not selected_id:
        render_empty_state(runs)
        return

    # Find selected run
    selected = next(((s, m) for s, m in runs if s.run_id == selected_id), None)
    if not selected:
        st.error("Projekt nicht gefunden.")
        return

    state, meta = selected
    scraped = _load_scraped_data(state)
    run_dir = OUTPUT_DIR / state.run_id

    # Header
    status_color = STATUS_COLORS.get(meta.akquise_status, "#9ca3af")
    st.markdown(
        f"# {state.domain} &nbsp; {_status_badge(meta.akquise_status, status_color)}",
        unsafe_allow_html=True,
    )

    # Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Ubersicht",
        "Akquise",
        "Audit",
        "Redesign",
        "Paket",
    ])

    with tab1:
        render_tab_overview(state, scraped)

    with tab2:
        render_tab_akquise(state, meta)

    with tab3:
        render_tab_audit(state)

    with tab4:
        render_tab_redesign(state)

    with tab5:
        render_tab_paket(state)


if __name__ == "__main__":
    main()
