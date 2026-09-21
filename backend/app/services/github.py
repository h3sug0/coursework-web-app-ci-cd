import httpx
from fastapi import HTTPException, status

class GitHubService:
    def __init__(self, token: str, base_url: str = "https://api.github.com"):
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def verify_token(self) -> dict:
        """Проверяет валидность токена и возвращает логин пользователя."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(f"{self.base_url}/user", headers=self.headers)
            except httpx.RequestError as exc:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"Не удалось связаться с GitHub API: {exc}"
                )

            if response.status_code == 401:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Недействительный токен GitHub (Bad credentials)"
                )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Ошибка GitHub API: {response.text}"
                )
            return response.json()

    async def get_user_repositories(self) -> list[dict]:
        """Получает список доступных репозиториев (до 100 последних)."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                f"{self.base_url}/user/repos",
                headers=self.headers,
                params={"per_page": 100, "sort": "updated"}
            )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Не удалось получить репозитории: {response.text}"
                )
            return response.json()