from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="TINTIN_", extra="ignore")

    llm_provider: str = "anthropic"
    anthropic_model: str = "claude-sonnet-4-6"
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b-instruct"

    public_name: str = "Tintin"

    corpus_dir: Path = Path("./corpus")
    chroma_dir: Path = Path("./data/chroma")
    sqlite_path: Path = Path("./data/tintin.sqlite")

    snapshot_date: str = "2026-05-21"
    default_tax_year: int = 2025
    allowed_hosts: str = "irs.gov,www.irs.gov,uscode.house.gov,www.ecfr.gov,ecfr.gov"
    daily_token_cap: int = 200_000

    oidc_issuer: str = "https://accounts.google.com"
    oidc_client_id: str = ""
    oidc_client_secret: str = ""
    oidc_redirect_uri: str = "http://localhost:8501/auth/callback"

    @property
    def allowed_host_set(self) -> set[str]:
        return {h.strip().lower() for h in self.allowed_hosts.split(",") if h.strip()}


settings = Settings()
