"""Settings for configuring the MLX backend."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class MLXSettings(BaseSettings):
    """Configuration values for running models with the MLX runtime."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    model: str = Field(
        default="mlx-community/Llama-3.1-8B-Instruct-4bit",
        description="Default MLX model identifier.",
        alias="OBS_GRAPHS_MLX_MODEL",
    )
    max_tokens: int = Field(
        default=1024,
        ge=1,
        description="Maximum number of tokens to generate per request.",
        alias="OBS_GRAPHS_MLX_MAX_TOKENS",
    )
    temperature: float = Field(
        default=0.2,
        ge=0.0,
        description="Sampling temperature for MLX generation.",
        alias="OBS_GRAPHS_MLX_TEMPERATURE",
    )
    top_p: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Top-p (nucleus) sampling parameter.",
        alias="OBS_GRAPHS_MLX_TOP_P",
    )
