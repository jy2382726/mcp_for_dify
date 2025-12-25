# -*- coding: utf-8 -*-
"""
MinIO MCP 工具插件

提供基于 MinIO 对象存储的文件操作能力，包括文件上传、信息查询和删除。
"""
from app.mcp.server import mcp
from app.services.minio_service import get_minio_service
from app.core.logger import logger
import base64
import json
from io import BytesIO

minio_service = get_minio_service()

# @mcp.tool()
# async def upload_file_content(file: str, filename: str, object_name: str = None, original_url: str = None) -> str:
#     """
#     MinIO 文件上传工具
    
#     接收 Base64 编码的文件内容并上传到 MinIO 对象存储。
    
#     Args:
#         file: Base64 编码的文件内容字符串。
#         filename: 文件名（包含扩展名，如 "test.txt"）。
#         object_name: (可选) 对象名称，如果未提供，将使用原始文件名生成。
#         original_url: (可选) 文件原始URL地址。
        
#     Returns:
#         str: 包含上传结果的 JSON 字符串。
#              成功示例: {"object_name": "...", "preview_url": "...", ...}
#              失败示例: {"error": "..."}
#     """
#     logger.info(f"MCP Tool 'upload_file_content' called for file: {filename}")
#     try:
#         # Decode base64 in thread pool to avoid blocking event loop
#         import asyncio
#         loop = asyncio.get_running_loop()
        
#         def decode_content():
#             return base64.b64decode(file)
            
#         file_data = await loop.run_in_executor(None, decode_content)
#         file_obj = BytesIO(file_data)
        
#         result = await minio_service.upload_file(
#             file_obj=file_obj, 
#             filename=filename, 
#             object_name=object_name, 
#             original_url=original_url
#         )
#         return json.dumps(result, ensure_ascii=False)
#     except Exception as e:
#         logger.error(f"Upload failed: {e}")
#         return json.dumps({"error": str(e)}, ensure_ascii=False)

@mcp.tool()
async def get_file_info(object_name: str) -> str:
    """
    MinIO 文件信息查询工具
    
    根据对象名称查询文件的元数据信息。
    
    Args:
        object_name: 对象存储中的对象名称（路径）。
        
    Returns:
        str: 包含文件信息的 JSON 字符串。
             成功示例: {"size": 1024, "content_type": "text/plain", ...}
             失败示例: {"error": "..."}
    """
    logger.info(f"MCP Tool 'get_file_info' called for object: {object_name}")
    try:
        result = await minio_service.get_file_info(object_name)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Get info failed: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)

@mcp.tool()
async def delete_file(object_name: str) -> str:
    """
    MinIO 文件删除工具
    
    从 MinIO 对象存储中删除指定的文件。
    
    Args:
        object_name: 要删除的对象名称（路径）。
        
    Returns:
        str: 包含删除结果的 JSON 字符串。
             成功示例: {"deleted": true, "object_name": "..."}
             失败示例: {"error": "..."}
    """
    logger.info(f"MCP Tool 'delete_file' called for object: {object_name}")
    try:
        result = await minio_service.delete_file(object_name)
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Delete failed: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)
