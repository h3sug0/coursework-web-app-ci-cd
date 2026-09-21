from pydantic import BaseModel

class CIProviderCreate(BaseModel):
    name: str = "My GitHub"
    provider_type: str = "GITHUB"
    token: str
    api_url: str = "https://api.github.com"

class CIProviderResponse(BaseModel):
    id: int
    name: str
    provider_type: str
    api_url: str
    is_valid: bool

    class Config:
        from_attributes = True