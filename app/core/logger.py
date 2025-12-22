import sys
from loguru import logger
from app.core.config import get_settings

settings = get_settings()

def setup_logging():
    """
    配置日志系统
    使用 Loguru 替代标准 logging
    """
    # 移除默认 handler
    logger.remove()

    # 添加控制台输出
    logger.add(
        sys.stderr,
        level=settings.LOG_LEVEL,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    )

    # 添加文件轮转日志 (仅在生产环境或需要时开启，这里作为示例)
    logger.add(
        "logs/app.log",
        rotation="500 MB",
        retention="10 days",
        level="INFO",
        compression="zip",
        enqueue=True
    )

    logger.info(f"Logger initialized with level: {settings.LOG_LEVEL}")
