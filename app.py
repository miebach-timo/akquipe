"""akquipe Dashboard v2 — Streamlit UI"""

import asyncio
import json
import subprocess
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
from shared.run_state import RunState, Status, RedesignParams

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
    return (
        f'<span style="background:{color};color:#fff;padding:2px 10px;'
        f'border-radius:12px;font-size:12px;font-weight:600">{label}</span>'
    )


def _stage_badge(status: Status) -> str:
    cfg = {
        Status.DONE:    ("#22c55e", "Fertig"),
        Status.FAILED:  ("#ef4444", "Fehler"),
        Status.RUNNING: ("#f97316", "Läuft"),
        Status.SKIPPED: ("#9ca3af", "Übersprungen"),
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


def _reload_state(state: RunState) -> RunState:
    try:
        return RunState.load(state.run_id, OUTPUT_DIR)
    except Exception:
        return state


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

def render_sidebar(runs: list[tuple[RunState, ClientMeta]]) -> Optional[str]:
    with st.sidebar:
        st.markdown("## akquipe v2")
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
# Tab 1 — Übersicht
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

    # 6-Stage Pipeline Status
    st.markdown("**Pipeline-Status**")
    stage_cols = st.columns(6)
    stages = [
        ("Scraper", state.scraper.status),
        ("Vault", state.vault.status),
        ("Imitat", state.imitate.status),
        ("Audit", state.audit.status),
        ("Redesign", state.redesign.status),
        ("Paket", state.package.status),
    ]
    for col, (name, status) in zip(stage_cols, stages):
        with col:
            st.markdown(
                f"<center><small>{name}</small><br>{_stage_badge(status)}</center>",
                unsafe_allow_html=True,
            )

    st.markdown("")

    # Audit Scores (4 categories)
    if state.audit.scores:
        st.markdown("**Audit-Scores**")
        score_cols = st.columns(4)
        labels = {
            "accessibility": "Barrierefreiheit",
            "seo": "SEO",
            "ux_ui": "UX/UI",
            "usability": "Usability",
        }
        for col, (key, label) in zip(score_cols, labels.items()):
            score = state.audit.scores.get(key, 0)
            with col:
                color = _score_color(score)
                st.markdown(
                    f'<div style="text-align:center">'
                    f'<div style="font-size:32px;font-weight:700;color:{color}">{score}</div>'
                    f'<div style="font-size:11px;color:#6b7280">{label}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

        # Review status indicator
        if state.audit.manual_review_approved:
            st.success(
                f"Review freigegeben"
                + (f" am {state.audit.manual_review_approved_at[:10]}" if state.audit.manual_review_approved_at else "")
            )
        elif state.audit.status == Status.DONE:
            st.warning("Audit fertig — Review noch ausstehend (Tab: Audit)")

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
        # also show mobile/tablet
        for extra_key in ("mobile_screenshot_path", "tablet_screenshot_path"):
            ep = scraped.get(extra_key)
            if ep and Path(ep).exists() and ep not in shots:
                shots.append(ep)

        if shots:
            shot_cols = st.columns(min(len(shots), 3))
            for col, path in zip(shot_cols, shots[:3]):
                with col:
                    try:
                        st.image(path, use_container_width=True, caption=Path(path).stem)
                    except Exception:
                        pass


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
            "Nächste Aktion",
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
# Tab 3 — Imitat
# ---------------------------------------------------------------------------

def render_tab_imitat(state: RunState, scraped: Optional[dict]) -> None:
    st.markdown("### 1:1 Website-Imitat")

    if state.imitate.status != Status.DONE:
        st.info("Imitat noch nicht erstellt. Stage 3 starten:")
        st.code(f"python pipeline.py run {state.url} --stages 3")
        return

    project_path = Path(state.imitate.project_path) if state.imitate.project_path else None

    if project_path and project_path.exists():
        st.success(f"Imitat-Projekt bereit: `{project_path}`")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Ordner öffnen", key="open_imitat"):
                _open_folder(str(project_path))
        with col2:
            st.code(f"cd \"{project_path}\"\nnpm install\nnpm run dev", language="bash")

        # Original vs Imitat screenshot comparison
        orig_shots = []
        if scraped and scraped.get("screenshots"):
            orig_shots = [p for p in scraped["screenshots"] if Path(p).exists()]

        if orig_shots:
            st.markdown("---")
            st.markdown("**Original vs. Imitat**")
            c1, c2 = st.columns(2)
            with c1:
                st.caption("Original")
                try:
                    st.image(orig_shots[0], use_container_width=True)
                except Exception:
                    st.caption("Kein Screenshot verfügbar")
            with c2:
                st.caption("Imitat (lokal starten: localhost:3000)")
                st.info("Starte `npm run dev` und öffne localhost:3000 zum Vergleich.")

        # Brand tokens
        brand_file = project_path / "src" / "lib" / "brand.ts"
        if brand_file.exists():
            with st.expander("Brand-Tokens anzeigen (src/lib/brand.ts)"):
                st.code(brand_file.read_text(encoding="utf-8"), language="typescript")

        # DESIGN.md
        if state.vault.folder_path:
            design_md = Path(state.vault.folder_path) / "DESIGN.md"
            if design_md.exists():
                with st.expander("DESIGN.md anzeigen"):
                    st.markdown(design_md.read_text(encoding="utf-8"))
    else:
        st.warning("Imitat-Projektordner nicht gefunden.")


# ---------------------------------------------------------------------------
# Tab 4 — Audit (mit manuellem Review-Checkpoint)
# ---------------------------------------------------------------------------

def render_tab_audit(state: RunState) -> None:
    st.markdown("### Audit-Report")

    if state.audit.status != Status.DONE:
        st.info("Audit noch nicht ausgeführt. Stage 4 starten:")
        st.code(f"python pipeline.py run {state.url} --stages 4")
        return

    # Download buttons
    col1, col2 = st.columns(2)
    with col1:
        if state.audit.report_pdf_path and Path(state.audit.report_pdf_path).exists():
            st.download_button(
                "Audit-Report (PDF)",
                Path(state.audit.report_pdf_path).read_bytes(),
                file_name=f"audit_{state.domain}.pdf",
                mime="application/pdf",
            )
    with col2:
        if state.audit.report_md_path and Path(state.audit.report_md_path).exists():
            st.download_button(
                "Audit-Report (Markdown)",
                Path(state.audit.report_md_path).read_bytes(),
                file_name=f"audit_{state.domain}.md",
                mime="text/markdown",
            )

    # Scores — 4 categories
    if state.audit.scores:
        st.markdown("---")
        labels = {
            "accessibility": "Barrierefreiheit",
            "seo": "SEO",
            "ux_ui": "UX/UI",
            "usability": "Usability",
        }
        score_cols = st.columns(4)
        for col, (key, label) in zip(score_cols, labels.items()):
            score = state.audit.scores.get(key, 0)
            with col:
                st.metric(label, f"{score}/100")
                st.progress(score / 100)

    # Findings
    if state.audit.findings_count:
        st.markdown("---")
        st.markdown("**Befunde nach Kategorie**")
        fc_cols = st.columns(4)
        for col, (key, label) in zip(fc_cols, {
            "accessibility": "Barrierefreiheit",
            "seo": "SEO",
            "ux_ui": "UX/UI",
            "usability": "Usability",
        }.items()):
            with col:
                st.metric(label, state.audit.findings_count.get(key, 0))

    # Report Markdown
    if state.audit.report_md_path and Path(state.audit.report_md_path).exists():
        st.markdown("---")
        content = Path(state.audit.report_md_path).read_text(encoding="utf-8")
        if content.startswith("---"):
            end = content.find("---", 3)
            if end > 0:
                content = content[end + 3:].lstrip()
        with st.expander("Vollständiger Report anzeigen", expanded=False):
            st.markdown(content)

    # ── Manual Review Checkpoint ──────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### Mein Review")

    if state.audit.manual_review_approved:
        approved_at = state.audit.manual_review_approved_at or "—"
        st.success(f"Review freigegeben am {approved_at[:10]}")
        if state.audit.manual_review_notes:
            st.markdown(f"**Meine Anmerkungen:** {state.audit.manual_review_notes}")

        col_rev1, col_rev2 = st.columns(2)
        with col_rev1:
            st.info("Stage 5 (Redesign) kann jetzt gestartet werden.")
        with col_rev2:
            st.code("python pipeline.py resume " + state.run_id + " --stages 5,6")

    else:
        st.warning("Warte auf Review-Freigabe. Lies den Audit-Report durch und gib ihn frei.")

        review_notes = st.text_area(
            "Meine Anmerkungen (optional)",
            height=100,
            placeholder="z.B. Kontrast-Problem bei Navigation besonders wichtig. CTA komplett überarbeiten.",
            key="review_notes_input",
        )

        if st.button("Audit freigeben und Stage 5 aktivieren", type="primary", key="approve_audit"):
            state.audit.manual_review_approved = True
            state.audit.manual_review_notes = review_notes
            state.audit.manual_review_approved_at = datetime.now().isoformat()
            state.save(OUTPUT_DIR)
            st.success("Freigegeben! Stage 5 ist jetzt verfügbar.")
            st.rerun()


# ---------------------------------------------------------------------------
# Tab 5 — Redesign (iterativ mit Taste-Dials)
# ---------------------------------------------------------------------------

def render_tab_redesign(state: RunState) -> None:
    st.markdown("### Redesign")

    if not state.audit.manual_review_approved:
        st.warning("Bitte zuerst den Audit im Tab 'Audit' freigeben.")
        return

    if state.audit.status != Status.DONE:
        st.info("Audit noch nicht abgeschlossen — Stage 4 zuerst.")
        return

    # Current redesign status
    if state.redesign.status == Status.DONE and state.redesign.iterations:
        latest = state.redesign.iterations[-1]
        project_path = Path(latest.project_path) if Path(latest.project_path).exists() else None

        st.success(f"Iteration {latest.iteration} fertig: `{latest.project_path}`")

        col1, col2 = st.columns(2)
        with col1:
            if project_path and st.button("Ordner öffnen", key="open_redesign"):
                _open_folder(str(project_path))
        with col2:
            if project_path:
                st.code(f"cd \"{project_path}\"\nnpm install\nnpm run dev", language="bash")

        # Brand tokens preview
        if project_path:
            brand_file = project_path / "src" / "lib" / "brand.ts"
            if brand_file.exists():
                with st.expander("Brand-Tokens der aktuellen Iteration"):
                    st.code(brand_file.read_text(encoding="utf-8"), language="typescript")

    elif state.redesign.status == Status.PENDING:
        st.info("Noch kein Redesign gestartet. Starte unten deine erste Iteration.")
    elif state.redesign.status == Status.FAILED:
        st.error(f"Redesign fehlgeschlagen: {state.redesign.error}")

    # Iterations history
    if state.redesign.iterations:
        st.markdown("---")
        st.markdown(f"**Iterationen ({len(state.redesign.iterations)})**")
        for it in reversed(state.redesign.iterations):
            with st.expander(
                f"Iteration {it.iteration} — V:{it.params.design_variance} M:{it.params.motion_intensity} D:{it.params.visual_density}",
                expanded=(it.iteration == state.redesign.current_iteration),
            ):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.markdown(f"**Style:** {it.params.style_direction}")
                    st.markdown(f"**Erstellt:** {it.created_at[:16]}")
                with col_b:
                    st.markdown(f"**Pfad:** `{it.project_path}`")
                if it.user_feedback:
                    st.markdown(f"**Feedback:** {it.user_feedback}")
                if Path(it.project_path).exists():
                    if st.button("Ordner öffnen", key=f"open_iter_{it.iteration}"):
                        _open_folder(it.project_path)

    # ── Neue Iteration starten ──────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### Neue Iteration starten")

    with st.form("redesign_form"):
        feedback = st.text_area(
            "Feedback zur letzten Iteration",
            height=80,
            placeholder="z.B. Die Farben wirken zu dunkel, CTA sollte mehr hervorstechen.",
        )

        col1, col2, col3 = st.columns(3)
        with col1:
            variance = st.slider("Design-Variance", 1, 10, 5, help="1=konservativ · 10=experimentell")
        with col2:
            motion = st.slider("Motion-Intensität", 1, 10, 3, help="1=statisch · 10=viel Animation")
        with col3:
            density = st.slider("Visual-Density", 1, 10, 5, help="1=luftig · 10=informationsdicht")

        style_options = ["auto", "modern-corporate", "minimal", "bold", "b2b-tech", "healthcare", "craft", "lifestyle"]
        style = st.selectbox("Style-Direction", style_options)

        submitted = st.form_submit_button("Neue Iteration starten", type="primary")

    if submitted:
        params = RedesignParams(
            design_variance=variance,
            motion_intensity=motion,
            visual_density=density,
            style_direction=style,
        )
        st.info("Redesign läuft... Das dauert 1–3 Minuten.")
        with st.spinner("Generiere Komponenten..."):
            from config.settings import get_settings
            settings = get_settings()
            from stages.stage5_redesign.redesign_agent import run_redesign_iteration
            state = asyncio.run(run_redesign_iteration(state, settings, params, feedback))
            state.save(OUTPUT_DIR)
        st.success(f"Iteration {state.redesign.current_iteration} fertig!")
        st.rerun()


# ---------------------------------------------------------------------------
# Tab 6 — Paket
# ---------------------------------------------------------------------------

def render_tab_paket(state: RunState) -> None:
    st.markdown("### Kundenpaket")

    if state.package.status != Status.DONE:
        st.info("Paket noch nicht erstellt. Stage 6 starten:")
        st.code(f"python pipeline.py run {state.url} --stages 6")
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

    # Before/After score comparison
    if state.audit.scores:
        st.markdown("---")
        st.markdown("**Vorher/Nachher (Audit-Scores)**")
        labels = {"accessibility": "Barrierefreiheit", "seo": "SEO", "ux_ui": "UX/UI", "usability": "Usability"}
        score_cols = st.columns(4)
        for col, (key, label) in zip(score_cols, labels.items()):
            orig = state.audit.scores.get(key, 0)
            target = min(orig + 25, 95)
            with col:
                color = _score_color(orig)
                st.markdown(
                    f'<div style="text-align:center">'
                    f'<div style="font-size:13px;color:#6b7280">{label}</div>'
                    f'<div style="font-size:20px;font-weight:700;color:{color}">{orig} → {target}</div>'
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
        ("03_Redesign_Website.zip", "Redesign-Website-ZIP"),
        ("03_Imitat_Website.zip", "Imitat-Website-ZIP"),
        ("03_Rekonstruierte_Website.zip", "Website-ZIP (legacy)"),
        ("04_Preisvorschlag.md", "Preisvorschlag"),
        ("05_Changelog.md", "Changelog (Vorher/Nachher)"),
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

    # Anschreiben preview
    anschreiben = package_dir / "02_Anschreiben.md"
    if anschreiben.exists():
        st.markdown("---")
        with st.expander("Anschreiben-Vorschau"):
            st.markdown(anschreiben.read_text(encoding="utf-8"))

    # Changelog preview
    changelog = package_dir / "05_Changelog.md"
    if changelog.exists():
        with st.expander("Changelog-Vorschau"):
            st.markdown(changelog.read_text(encoding="utf-8"))

    # Preisvorschlag preview
    preis = package_dir / "04_Preisvorschlag.md"
    if preis.exists():
        with st.expander("Preisvorschlag-Vorschau"):
            st.markdown(preis.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Empty state
# ---------------------------------------------------------------------------

def render_empty_state(runs: list) -> None:
    st.markdown("## Willkommen bei akquipe v2")
    st.markdown("Deine UX/UI Akquise-Pipeline — 6 Stages, iteratives Redesign, manuelle Review-Kontrolle.")
    st.markdown("---")

    if not runs:
        st.info("Noch keine Projekte vorhanden. Starte deinen ersten Run:")
        st.code("python pipeline.py run https://kundenwebsite.de")
    else:
        st.markdown(f"**{len(runs)} Projekte** in der Sidebar — klicke ein Projekt an.")

        st.markdown("---")
        st.markdown("### Alle Projekte")
        for state, meta in runs[:20]:
            sc = STATUS_COLORS.get(meta.akquise_status, "#9ca3af")
            badge = _status_badge(meta.akquise_status, sc)
            scores = state.audit.scores
            score_str = ""
            if scores:
                score_str = (
                    f" · A:{scores.get('accessibility','—')} "
                    f"S:{scores.get('seo','—')} "
                    f"UX:{scores.get('ux_ui','—')} "
                    f"US:{scores.get('usability','—')}"
                )
            review_str = " ✅" if state.audit.manual_review_approved else ""
            st.markdown(
                f"{badge} &nbsp; **{state.domain}** &nbsp; "
                f"<span style='color:#6b7280;font-size:13px'>"
                f"{state.started_at.strftime('%d.%m.%Y')}{score_str}{review_str}"
                f"</span>",
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

    selected = next(((s, m) for s, m in runs if s.run_id == selected_id), None)
    if not selected:
        st.error("Projekt nicht gefunden.")
        return

    state, meta = selected
    scraped = _load_scraped_data(state)

    status_color = STATUS_COLORS.get(meta.akquise_status, "#9ca3af")
    st.markdown(
        f"# {state.domain} &nbsp; {_status_badge(meta.akquise_status, status_color)}",
        unsafe_allow_html=True,
    )

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Übersicht",
        "Akquise",
        "Imitat",
        "Audit",
        "Redesign",
        "Paket",
    ])

    with tab1:
        render_tab_overview(state, scraped)

    with tab2:
        render_tab_akquise(state, meta)

    with tab3:
        render_tab_imitat(state, scraped)

    with tab4:
        render_tab_audit(state)

    with tab5:
        render_tab_redesign(state)

    with tab6:
        render_tab_paket(state)


if __name__ == "__main__":
    main()
