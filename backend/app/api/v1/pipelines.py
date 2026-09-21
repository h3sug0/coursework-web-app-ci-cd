from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.security import decrypt_token
from app.models.models import CIProvider, Pipeline, PipelineStep, Repository, User
from app.schemas.pipeline import MetricsSummary, PipelineResponse
from app.services.github import GitHubService

router = APIRouter(tags=["Pipelines & Dispatcher"])

def normalize_status(gh_status: str, conclusion: str | None) -> str:
    """Приводит статусы GitHub Actions к единому стандарту системы."""
    if gh_status in ["queued", "waiting", "requested"]:
        return "QUEUED"
    if gh_status == "in_progress":
        return "RUNNING"
    if gh_status == "completed":
        if conclusion == "success":
            return "SUCCESS"
        if conclusion in ["failure", "timed_out", "action_required"]:
            return "FAILED"
        if conclusion in ["cancelled", "skipped"]:
            return "CANCELED"
    return "UNKNOWN"

@router.post("/pipelines/sync", summary="Синхронизировать пайплайны отслеживаемых репозиториев")
async def sync_pipelines(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(Repository, CIProvider)
        .join(CIProvider, Repository.provider_id == CIProvider.id)
        .where(CIProvider.user_id == current_user.id, Repository.is_monitored.is_(True))
    )
    result = await db.execute(query)
    repos_with_providers = result.all()

    synced_count = 0
    for repo, provider in repos_with_providers:
        token = decrypt_token(provider.encrypted_token)
        service = GitHubService(token=token, base_url=provider.api_url)
        
        try:
            runs = await service.get_workflow_runs(repo.full_name, per_page=10)
        except Exception:
            continue

        for run in runs:
            ext_id = str(run["id"])
            norm_status = normalize_status(run.get("status"), run.get("conclusion"))
            
            # Парсинг дат
            started_at = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00")) if run.get("created_at") else None
            finished_at = datetime.fromisoformat(run["updated_at"].replace("Z", "+00:00")) if run.get("updated_at") and run.get("status") == "completed" else None
            duration = int((finished_at - started_at).total_seconds()) if (started_at and finished_at) else 0

            p_res = await db.execute(
                select(Pipeline).where(
                    Pipeline.repository_id == repo.id,
                    Pipeline.external_run_id == ext_id
                )
            )
            pipeline = p_res.scalars().first()

            commit_msg = run.get("head_commit", {}).get("message") if run.get("head_commit") else run.get("display_title")
            author = run.get("actor", {}).get("login")

            if not pipeline:
                pipeline = Pipeline(
                    repository_id=repo.id,
                    external_run_id=ext_id,
                    branch=run.get("head_branch") or "main",
                    commit_sha=run.get("head_sha", "")[:7],
                    commit_message=commit_msg,
                    author_name=author,
                    status=norm_status,
                    duration_sec=duration,
                    started_at=started_at,
                    finished_at=finished_at,
                )
                db.add(pipeline)
                await db.flush()

                # Сохраняем шаги (jobs)
                jobs = await service.get_run_jobs(repo.full_name, ext_id)
                for job in jobs:
                    step = PipelineStep(
                        pipeline_id=pipeline.id,
                        name=job.get("name", "Unnamed Step"),
                        stage="build",
                        status=normalize_status(job.get("status"), job.get("conclusion")),
                        duration_sec=0
                    )
                    db.add(step)
            else:
                pipeline.status = norm_status
                pipeline.duration_sec = duration
                pipeline.finished_at = finished_at

            synced_count += 1

    await db.commit()
    return {"message": f"Синхронизация завершена. Обработано запусков: {synced_count}"}

@router.get("/pipelines", response_model=list[PipelineResponse], summary="Список пайплайнов с фильтрами")
async def list_pipelines(
    repo_id: int | None = Query(None, description="ID репозитория"),
    status: str | None = Query(None, description="QUEUED, RUNNING, SUCCESS, FAILED"),
    branch: str | None = Query(None, description="Ветка"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(Pipeline)
        .join(Repository, Pipeline.repository_id == Repository.id)
        .join(CIProvider, Repository.provider_id == CIProvider.id)
        .where(CIProvider.user_id == current_user.id)
        .options(selectinload(Pipeline.steps), selectinload(Pipeline.repository))
        .order_by(Pipeline.started_at.desc().nullslast())
    )

    if repo_id:
        query = query.where(Pipeline.repository_id == repo_id)
    if status:
        query = query.where(Pipeline.status == status.upper())
    if branch:
        query = query.where(Pipeline.branch == branch)

    result = await db.execute(query)
    pipelines = result.scalars().all()

    # Проставляем имя репозитория для фронтенда
    output = []
    for p in pipelines:
        item = PipelineResponse.model_validate(p)
        item.repo_name = p.repository.full_name
        output.append(item)
    return output

@router.post("/pipelines/{pipeline_id}/rerun", summary="Перезапуск пайплайна (Re-run)")
async def rerun_pipeline(
    pipeline_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(Pipeline, Repository, CIProvider)
        .join(Repository, Pipeline.repository_id == Repository.id)
        .join(CIProvider, Repository.provider_id == CIProvider.id)
        .where(Pipeline.id == pipeline_id, CIProvider.user_id == current_user.id)
    )
    res = await db.execute(query)
    row = res.first()
    if not row:
        raise HTTPException(status_code=404, detail="Пайплайн не найден")

    pipeline, repo, provider = row
    token = decrypt_token(provider.encrypted_token)
    service = GitHubService(token=token, base_url=provider.api_url)

    await service.rerun_workflow(repo.full_name, pipeline.external_run_id)

    pipeline.status = "QUEUED"
    await db.commit()
    return {"message": "Запрос на повторный запуск успешно отправлен", "status": "QUEUED"}

@router.get("/metrics/summary", response_model=MetricsSummary, summary="Сводные метрики стабильности сборок")
async def get_metrics_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    base_filter = (
        select(Pipeline.status)
        .join(Repository, Pipeline.repository_id == Repository.id)
        .join(CIProvider, Repository.provider_id == CIProvider.id)
        .where(CIProvider.user_id == current_user.id)
    )
    result = await db.execute(base_filter)
    statuses = result.scalars().all()

    total_runs = len(statuses)
    success_count = sum(1 for s in statuses if s == "SUCCESS")
    failed_count = sum(1 for s in statuses if s == "FAILED")
    running_count = sum(1 for s in statuses if s in ["RUNNING", "QUEUED"])

    rate = round((success_count / total_runs * 100), 1) if total_runs > 0 else 0.0

    return MetricsSummary(
        total_runs=total_runs,
        success_rate=rate,
        running_count=running_count,
        failed_count=failed_count
    )