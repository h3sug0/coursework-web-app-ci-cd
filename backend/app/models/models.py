from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    providers: Mapped[list["CIProvider"]] = relationship(
        "CIProvider", back_populates="user", cascade="all, delete-orphan"
    )

class CIProvider(Base):
    __tablename__ = "ci_providers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    provider_type: Mapped[str] = mapped_column(String(32), default="GITHUB")
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    api_url: Mapped[str] = mapped_column(String(255), default="https://api.github.com")
    encrypted_token: Mapped[str] = mapped_column(Text, nullable=False)
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True)

    user: Mapped["User"] = relationship("User", back_populates="providers")
    repositories: Mapped[list["Repository"]] = relationship(
        "Repository", back_populates="provider", cascade="all, delete-orphan"
    )

class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    provider_id: Mapped[int] = mapped_column(ForeignKey("ci_providers.id", ondelete="CASCADE"), nullable=False)
    external_id: Mapped[str] = mapped_column(String(100), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    default_branch: Mapped[str] = mapped_column(String(100), default="main")
    web_url: Mapped[str] = mapped_column(String(512), nullable=False)
    is_monitored: Mapped[bool] = mapped_column(Boolean, default=True)

    provider: Mapped["CIProvider"] = relationship("CIProvider", back_populates="repositories")
    pipelines: Mapped[list["Pipeline"]] = relationship(
        "Pipeline", back_populates="repository", cascade="all, delete-orphan"
    )

class Pipeline(Base):
    __tablename__ = "pipelines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    repository_id: Mapped[int] = mapped_column(ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    external_run_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    branch: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    commit_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    commit_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    author_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    status: Mapped[str] = mapped_column(String(32), index=True, default="QUEUED")
    duration_sec: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    repository: Mapped["Repository"] = relationship("Repository", back_populates="pipelines")
    steps: Mapped[list["PipelineStep"]] = relationship(
        "PipelineStep", back_populates="pipeline", cascade="all, delete-orphan"
    )

class PipelineStep(Base):
    __tablename__ = "pipeline_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    pipeline_id: Mapped[int] = mapped_column(ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    stage: Mapped[str] = mapped_column(String(64), default="default")
    status: Mapped[str] = mapped_column(String(32), default="QUEUED")
    log_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_sec: Mapped[int] = mapped_column(Integer, default=0)

    pipeline: Mapped["Pipeline"] = relationship("Pipeline", back_populates="steps")