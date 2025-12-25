from mcp.server.fastmcp import FastMCP
from app.core.config import get_settings

settings = get_settings()

# 初始化 FastMCP 服务器实例
# dependencies: 依赖注入列表，如果需要的话
mcp = FastMCP(
    name=settings.MCP_SERVER_NAME,
    dependencies=[],
    host=settings.HOST, # 允许外部访问，同时禁用默认的 localhost DNS 重绑定保护
    port=settings.PORT  # 显式设置端口
)

def init_mcp():
    """
    可以在这里进行 MCP 服务的初始化操作
    例如加载插件等
    """
    # 动态导入插件以触发注册
    import app.plugins.echo
    import app.plugins.text_splitter
    import app.plugins.minio_tools
