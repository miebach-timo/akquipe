from datetime import datetime
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


AKQUISE_STATI = [
    "Neu",
    "Angefragt",
    "Antwort erhalten",
    "Gewonnen",
    "Verloren",
    "Abgebrochen",
]

STATUS_COLORS = {
    "Neu": "#9ca3af",
    "Angefragt": "#3b82f6",
    "Antwort erhalten": "#f97316",
    "Gewonnen": "#22c55e",
    "Verloren": "#ef4444",
    "Abgebrochen": "#4b5563",
}


class ClientMeta(BaseModel):
    akquise_status: str = "Neu"
    anfrage_datum: Optional[str] = None
    anfrage_notiz: str = ""
    antwort_datum: Optional[str] = None
    antwort_text: str = ""
    naechste_aktion: str = ""
    updated_at: Optional[str] = None


def _meta_path(run_dir: Path) -> Path:
    return run_dir / "client_meta.json"


def load_client_meta(run_dir: Path) -> ClientMeta:
    path = _meta_path(run_dir)
    if path.exists():
        return ClientMeta.model_validate_json(path.read_text(encoding="utf-8"))
    return ClientMeta()


def save_client_meta(run_dir: Path, meta: ClientMeta) -> None:
    meta.updated_at = datetime.now().isoformat()
    _meta_path(run_dir).write_text(meta.model_dump_json(indent=2), encoding="utf-8")
