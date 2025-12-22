import uvicorn
import os
import sys

# 将当前目录添加到 sys.path，确保可以找到 app 包
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import get_settings

if __name__ == "__main__":
    settings = get_settings()
    # 使用 uvicorn 运行应用
    # reload=True 在开发模式下很有用，生产环境建议关闭
    uvicorn.run(
        "app.main:app", 
        host=settings.HOST, 
        port=settings.PORT, 
        reload=settings.APP_ENV == "development"
    )
