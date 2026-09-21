from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.security import encrypt_token, decrypt_token
from app.models.models import CIProvider, Repository, User
from app.schemas.provider import CIProviderCreate, CIProviderResponse
from app.schemas.repository import RepositoryResponse, RepositoryToggle
from app.services.github import GitHubService

router = APIRouter(tags=["Providers & Repositories"])

@router.post("/providers", response_model=CIProviderResponse, status_code=status.HTTP_201_CREATED)
async def add_provider(
    provider_in: CIProviderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # 1. Проверяем валидность токена в GitHub
    github_service = GitHubService(token=provider_in.token, base_url=provider_in.api_url)
    await github_service.verify_token()

    # 2. Шифруем токен и сохраняем подключение в БД
    provider = CIProvider(
        user_id=current_user.id,
        name=provider_in.name,
        provider_type=provider_in.provider_type.upper(),
        api_url=provider_in.api_url,
        encrypted_token=encrypt_token(provider_in.token),
        is_valid=True
    )
    db.add(provider)
    await db.commit()
    await db.refresh(provider)
    return provider

@router.get("/providers", response_model=list[CIProviderResponse])
async def list_providers(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(CIProvider).where(CIProvider.user_id == current_user.id))
    return result.scalars().all()

@router.post("/providers/{provider_id}/sync", response_model=list[RepositoryResponse])
async def sync_repositories(
    provider_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Получаем провайдера
    result = await db.execute(
        select(CIProvider).where(CIProvider.id == provider_id, CIProvider.user_id == current_user.id)
    )
    provider = result.scalars().first()
    if not provider:
        raise HTTPException(status_code=404, detail="Провайдер не найден")

    # Расшифровываем токен и загружаем репозитории из GitHub
    plain_token = decrypt_token(provider.encrypted_token)
    service = GitHubService(token=plain_token, base_url=provider.api_url)
    repos_data = await service.get_user_repositories()

    saved_repos = []
    for item in repos_data:
        ext_id = str(item["id"])
        # Проверяем, есть ли уже этот репозиторий в БД
        repo_res = await db.execute(
            select(Repository).where(
                Repository.provider_id == provider.id,
                Repository.external_id == ext_id
            )
        )
        repo = repo_res.scalars().first()

        if not repo:
            repo = Repository(
                provider_id=provider.id,
                external_id=ext_id,
                full_name=item["full_name"],
                default_branch=item.get("default_branch", "main"),
                web_url=item["html_url"],
                is_monitored=True
            )
            db.add(repo)
        else:
            repo.full_name = item["full_name"]
            repo.default_branch = item.get("default_branch", "main")
            repo.web_url = item["html_url"]

        saved_repos.append(repo)

    await db.commit()
    for r in saved_repos:
        await db.refresh(r)
    return saved_repos

@router.get("/repositories", response_model=list[RepositoryResponse])
async def list_repositories(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(Repository)
        .join(CIProvider)
        .where(CIProvider.user_id == current_user.id)
        .order_by(Repository.full_name)
    )
    result = await db.execute(query)
    return result.scalars().all()

@router.patch("/repositories/{repo_id}", response_model=RepositoryResponse)
async def toggle_repository_monitoring(
    repo_id: int,
    payload: RepositoryToggle,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(Repository)
        .join(CIProvider)
        .where(Repository.id == repo_id, CIProvider.user_id == current_user.id)
    )
    result = await db.execute(query)
    repo = result.scalars().first()
    if not repo:
        raise HTTPException(status_code=404, detail="Репозиторий не найден")

    repo.is_monitored = payload.is_monitored
    await db.commit()
    await db.refresh(repo)
    return repo