from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    """
    应用配置类
    通过 Pydantic 管理环境变量，支持 .env 文件
    """
    # 应用基本配置
    APP_NAME: str = "MCP Service for Dify"
    APP_ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    
    # 服务监听配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # MCP 服务配置
    MCP_SERVER_NAME: str = "mcp-for-dify-server"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

@lru_cache()
def get_settings() -> Settings:
    """
    获取配置单例
    :return: Settings 实例
    """
    return Settings()
