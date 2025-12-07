"""Configuration management for ContextCatcher."""
import json
import os
from typing import Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class EmailConfig(BaseModel):
    """Email/IMAP configuration."""
    host: str = Field(default="imap.gmail.com")
    port: int = Field(default=993)
    username: str
    password: str
    use_ssl: bool = Field(default=True)


class FetchConfig(BaseModel):
    """Message fetching configuration."""
    lookback_hours: int = Field(default=24)
    lookback_minutes: Optional[int] = Field(default=None)  # If set, overrides lookback_hours
    strip_quotes: bool = Field(default=True)
    max_retries: int = Field(default=3)
    retry_backoff_base: float = Field(default=2.0)
    primary_only: bool = Field(default=False)  # If true, only fetch from primary inbox (Gmail)
    use_arrival_date: bool = Field(default=True)  # If true, use arrival date instead of sent date
    
    def get_lookback_hours(self) -> float:
        """Get lookback period in hours (supports minutes)."""
        if self.lookback_minutes is not None:
            return self.lookback_minutes / 60.0
        return float(self.lookback_hours)


class LLMConfig(BaseModel):
    """LLM/AI configuration."""
    enabled: bool = Field(default=False)
    provider: str = Field(default="openai")
    api_key: str = Field(default="")
    model: str = Field(default="gpt-3.5-turbo")


class StorageConfig(BaseModel):
    """Storage configuration."""
    dir: str = Field(default="./storage")
    index_file: str = Field(default="index.json")


class Config(BaseModel):
    """Main application configuration."""
    email: EmailConfig
    fetch: FetchConfig
    llm: LLMConfig
    storage: StorageConfig

    @classmethod
    def load(cls, config_path: str = "config.json") -> "Config":
        """
        Load configuration from file and environment variables.
        Environment variables take precedence over file values.
        """
        # Load from file if exists
        config_data = {}
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config_data = json.load(f)
        
        # Override with environment variables
        if os.getenv("EMAIL_HOST"):
            config_data.setdefault("email", {})["host"] = os.getenv("EMAIL_HOST")
        if os.getenv("EMAIL_PORT"):
            config_data.setdefault("email", {})["port"] = int(os.getenv("EMAIL_PORT"))
        if os.getenv("EMAIL_USERNAME"):
            config_data.setdefault("email", {})["username"] = os.getenv("EMAIL_USERNAME")
        if os.getenv("EMAIL_PASSWORD"):
            config_data.setdefault("email", {})["password"] = os.getenv("EMAIL_PASSWORD")
        
        if os.getenv("LOOKBACK_HOURS"):
            config_data.setdefault("fetch", {})["lookback_hours"] = int(os.getenv("LOOKBACK_HOURS"))
        
        if os.getenv("LLM_ENABLED"):
            config_data.setdefault("llm", {})["enabled"] = os.getenv("LLM_ENABLED").lower() == "true"
        if os.getenv("OPENAI_API_KEY"):
            config_data.setdefault("llm", {})["api_key"] = os.getenv("OPENAI_API_KEY")
        
        if os.getenv("STORAGE_DIR"):
            config_data.setdefault("storage", {})["dir"] = os.getenv("STORAGE_DIR")
        
        return cls(**config_data)
    
    def mask_sensitive(self) -> dict:
        """Return config dict with sensitive values masked."""
        data = self.model_dump()
        if data.get("email", {}).get("password"):
            data["email"]["password"] = "***"
        if data.get("llm", {}).get("api_key"):
            data["llm"]["api_key"] = "***"
        return data
