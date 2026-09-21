from datetime import datetime
from pydantic import BaseModel

class PipelineStepResponse(BaseModel):
    id: int
    name: str
    stage: str
    status: str
    duration_sec: int
    log_excerpt: str | None = None

    class Config:
        from_attributes = True

class PipelineResponse(BaseModel):
    id: int
    repository_id: int
    repo_name: str | None = None
    external_run_id: str
    branch: str
    commit_sha: str
    commit_message: str | None = None
    author_name: str | None = None
    status: str
    duration_sec: int
    started_at: datetime | None = None
    finished_at: datetime | None = None
    steps: list[PipelineStepResponse] = []

    class Config:
        from_attributes = True

class MetricsSummary(BaseModel):
    total_runs: int
    success_rate: float
    running_count: int
    failed_count: int