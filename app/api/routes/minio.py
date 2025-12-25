from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import Optional
from io import BytesIO
from app.services.minio_service import get_minio_service

router = APIRouter()
minio_service = get_minio_service()

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    object_name: Optional[str] = Form(None),
    original_url: Optional[str] = Form(None)
):
    """
    文件上传接口 (HTTP Form Data)
    
    Args:
        file: 要上传的文件
        object_name: (可选) 对象名称
        original_url: (可选) 文件原始URL
        
    Returns:
        dict: 上传结果
    """
    try:
        # 读取文件内容
        content = await file.read()
        file_obj = BytesIO(content)
        
        result = await minio_service.upload_file(
            file_obj=file_obj,
            filename=file.filename,
            object_name=object_name,
            original_url=original_url
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/delete")
async def delete_file(object_name: str):
    """
    删除文件接口
    
    Args:
        object_name: 要删除的对象名称
        
    Returns:
        dict: 删除结果
    """
    try:
        result = await minio_service.delete_file(object_name=object_name)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
