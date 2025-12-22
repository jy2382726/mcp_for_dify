from app.mcp.server import mcp
from app.services.echo_service import echo_service
from app.core.logger import logger

@mcp.tool()
async def echo_tool(message: str) -> str:
    """
    Echo 工具
    接收一个字符串并将其原样返回 (带有 Echo 前缀)。
    
    Args:
        message: 需要回显的字符串消息
        
    Returns:
        str: 回显的消息
    """
    logger.info(f"MCP Tool 'echo_tool' called with message: {message}")
    result = await echo_service.process_echo(message)
    return result
