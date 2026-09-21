from pydantic import BaseModel

class RepositoryResponse(BaseModel):
    id: int
    provider_id: int
    external_id: str
    full_name: str
    default_branch: str
    web_url: str
    is_monitored: bool

    class Config:
        from_attributes = True

class RepositoryToggle(BaseModel):
    is_monitored: bool