"""Configurações centrais da aplicação."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configurações carregadas de variáveis de ambiente."""

    app_name: str = Field(default="orcamento-ai")
    env: str = Field(default="development")
    log_level: str = Field(default="INFO")
    input_dir: str = Field(default="data/input")
    template_dir: str = Field(default="data/templates")
    output_dir: str = Field(default="data/output")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()

