from fastapi import FastAPI
from starlette.routing import Mount
from app.core.config import get_settings
from app.core.logger import setup_logging
from app.mcp.server import mcp, init_mcp

# 加载配置
settings = get_settings()

# 初始化日志
setup_logging()

# 初始化 MCP (加载插件)
init_mcp()

# 创建 FastAPI 应用
app = FastAPI(
    title=settings.APP_NAME,
    description="MCP Server for Dify Integration",
    version="1.0.0"
)

# 挂载 MCP SSE 服务
# Dify 将通过 SSE 连接到此端点
# 默认路径通常是 /sse，但我们可以根据需要挂载
# mcp.sse_app() 返回一个 Starlette 应用
app.mount("/mcp", mcp.sse_app())

@app.get("/health")
async def health_check():
    """
    健康检查端点
    """
    return {"status": "ok", "app_name": settings.APP_NAME}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
