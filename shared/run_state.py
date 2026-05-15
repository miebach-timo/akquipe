import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class Status(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


class ScraperState(BaseModel):
    status: Status = Status.PENDING
    data_path: Optional[str] = None
    screenshots_dir: Optional[str] = None
    pages_crawled: int = 0
    error: Optional[str] = None


class VaultState(BaseModel):
    status: Status = Status.PENDING
    folder_path: Optional[str] = None
    error: Optional[str] = None


class ImitateState(BaseModel):
    status: Status = Status.PENDING
    project_path: Optional[str] = None
    error: Optional[str] = None


class AuditState(BaseModel):
    status: Status = Status.PENDING
    report_md_path: Optional[str] = None
    report_pdf_path: Optional[str] = None
    scores: dict[str, int] = Field(default_factory=dict)
    findings_count: dict[str, int] = Field(default_factory=dict)
    manual_review_approved: bool = False
    manual_review_notes: str = ""
    manual_review_approved_at: Optional[str] = None
    error: Optional[str] = None


class RedesignParams(BaseModel):
    design_variance: int = 5      # 1=konservativ, 10=experimentell
    motion_intensity: int = 3     # 1=kein, 10=viel Animation
    visual_density: int = 5       # 1=luftig, 10=informationsdicht
    style_direction: str = "auto" # "modern-corporate", "minimal", "bold", ...


class RedesignIteration(BaseModel):
    iteration: int
    project_path: str
    params: RedesignParams = Field(default_factory=RedesignParams)
    user_feedback: str = ""
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class RedesignState(BaseModel):
    status: Status = Status.PENDING
    iterations: list[RedesignIteration] = Field(default_factory=list)
    current_iteration: int = 0
    project_path: Optional[str] = None
    error: Optional[str] = None


class ReconstructState(BaseModel):
    status: Status = Status.PENDING
    project_path: Optional[str] = None
    error: Optional[str] = None


class PackageState(BaseModel):
    status: Status = Status.PENDING
    zip_path: Optional[str] = None
    pricing_eur: Optional[float] = None
    error: Optional[str] = None


class RunState(BaseModel):
    run_id: str
    url: str
    domain: str
    started_at: datetime = Field(default_factory=datetime.now)
    scraper: ScraperState = Field(default_factory=ScraperState)
    vault: VaultState = Field(default_factory=VaultState)
    imitate: ImitateState = Field(default_factory=ImitateState)
    audit: AuditState = Field(default_factory=AuditState)
    redesign: RedesignState = Field(default_factory=RedesignState)
    reconstruct: ReconstructState = Field(default_factory=ReconstructState)  # kept for old runs
    package: PackageState = Field(default_factory=PackageState)

    def save(self, output_dir: Path) -> None:
        path = output_dir / self.run_id / "run_state.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.model_dump_json(indent=2), encoding="utf-8")

    @classmethod
    def load(cls, run_id: str, output_dir: Path) -> "RunState":
        path = output_dir / run_id / "run_state.json"
        return cls.model_validate_json(path.read_text(encoding="utf-8"))

    @classmethod
    def load_or_create(cls, run_id: str, url: str, domain: str, output_dir: Path) -> "RunState":
        path = output_dir / run_id / "run_state.json"
        if path.exists():
            return cls.load(run_id, output_dir)
        state = cls(run_id=run_id, url=url, domain=domain)
        state.save(output_dir)
        return state

    def run_dir(self, output_dir: Path) -> Path:
        return output_dir / self.run_id
