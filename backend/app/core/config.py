from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///./local_dev.db"
    SQL_MCP_URL: str = "http://localhost:9001"
    JIRA_MCP_URL: str = "http://localhost:9002"
    APIGW_MCP_URL: str = "http://localhost:9003"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
