from typing import Dict, Any
from app.mcp.server import mcp
from app.services.text_splitter_service import text_splitter_service
from app.core.logger import logger

@mcp.tool()
async def text_splitter(
    mode: str,
    content: str,
    parent_block_size: int = 1024,
    sub_block_size: int = 512,
    preview_url: str = "",
) -> Dict[str, Any]:
    """
    文本分块工具
    支持 PDF、Markdown 表格、纯文本（带预览链接）的分块处理。
    
    Args:
        mode: 分块模式。取值: 'pdf' (PDF文本), 'table' (Markdown表格), 'image' (纯文本带图片预览)
        content: 待处理的文本内容
        parent_block_size: 父块大小上限 (默认 1024)
        sub_block_size: 子块大小上限 (默认 512)
        preview_url: 当 mode=='image' 时必填的图片预览地址
        
    Returns:
        Dict[str, Any]: 包含处理后文本的字典 {"result": splited_content}
    """
    logger.info(f"MCP Tool 'text_splitter' called with mode: {mode}")
    result = text_splitter_service.split(
        mode=mode,
        content=content,
        parent_block_size=parent_block_size,
        sub_block_size=sub_block_size,
        preview_url=preview_url
    )
    return result
