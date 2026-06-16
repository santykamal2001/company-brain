from functools import lru_cache
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://brain:changeme@localhost:5432/company_brain"

    # ── Vector store ──────────────────────────────────────────────────────────
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "company_brain_chunks"

    # ── Task queue ────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── LLM ───────────────────────────────────────────────────────────────────
    llm_provider: Literal["claude", "openai", "azure", "ollama"] = "claude"
    llm_model: str = "claude-sonnet-4-6"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    azure_openai_api_key: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_deployment: str = ""
    ollama_base_url: str = "http://localhost:11434"

    extraction_llm_provider: Literal["claude", "openai", "azure", "ollama"] = "claude"
    extraction_llm_model: str = "claude-haiku-4-5"

    # ── Contextual Retrieval ──────────────────────────────────────────────────
    contextual_retrieval_enabled: bool = True
    context_llm_provider: Literal["claude", "openai", "azure", "ollama"] = "claude"
    context_llm_model: str = "claude-haiku-4-5"
    context_llm_use_prompt_caching: bool = True
    context_llm_use_batch_api: bool = True

    # ── Embeddings ────────────────────────────────────────────────────────────
    embedding_model: str = "BAAI/bge-large-en-v1.5"
    embedding_dim: int = 1024

    # ── Chunking ──────────────────────────────────────────────────────────────
    parent_chunk_size: int = 3500
    child_chunk_size: int = 512
    child_chunk_overlap: int = 50

    # ── Graph ─────────────────────────────────────────────────────────────────
    graph_enabled: bool = True
    graph_context_token_budget: int = 2000
    graph_traversal_depth: int = 1
    age_graph_name: str = "company_brain"

    # ── RBAC ──────────────────────────────────────────────────────────────────
    default_classification: str = "internal"
    confidential_keywords: str = (
        "salary,compensation,offer letter,termination,"
        "attorney,legal hold,acquisition,merger"
    )

    @property
    def confidential_keyword_list(self) -> list[str]:
        return [k.strip().lower() for k in self.confidential_keywords.split(",")]

    # ── SSO ───────────────────────────────────────────────────────────────────
    sso_enabled: bool = False
    saml_metadata_url: str = ""
    oidc_discovery_url: str = ""
    oidc_client_id: str = ""
    oidc_client_secret: str = ""
    scim_enabled: bool = False
    scim_token: str = ""

    # ── JWT ───────────────────────────────────────────────────────────────────
    jwt_secret: str = "CHANGE_THIS_IN_PRODUCTION_AT_LEAST_32_CHARS"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # ── File Upload ───────────────────────────────────────────────────────────
    upload_dir: str = "/app/uploads"
    max_upload_size_mb: int = 500


@lru_cache
def get_settings() -> Settings:
    return Settings()
