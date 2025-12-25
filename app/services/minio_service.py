# -*- coding: utf-8 -*-
"""
MinIO 文件服务模块

提供基于 MinIO 的文件上传、下载、删除和预览功能。
"""

import uuid
import asyncio
import urllib.parse
from datetime import datetime
from typing import Optional, Dict, Any
from functools import partial

# MinIO SDK imports
from minio.error import S3Error

# App imports
from app.core.minio_client import get_minio_client
from app.core.config import get_settings
from app.core.logger import logger
from app.exceptions import FileUploadError, FileDownloadError, FileValidationError

settings = get_settings()

class MinioService:
    """
    MinIO 文件服务类 (Async)
    """
    
    def __init__(self):
        self.client_manager = get_minio_client()
        # bucket_name 从配置获取，不直接存储在实例中，或者在需要时获取
        self.bucket_name = settings.MINIO_BUCKET_NAME
        self._bucket_checked = False

    async def _run_in_thread(self, func, *args, **kwargs):
        """在线程池中运行同步阻塞函数"""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, partial(func, *args, **kwargs))

    async def _ensure_bucket(self):
        """确保 Bucket 存在（线程安全且只检查一次）"""
        if not self._bucket_checked:
            await self._run_in_thread(self.client_manager.ensure_bucket_exists)
            self._bucket_checked = True

    def validate_file(self, file_obj, filename: str):
        """
        验证上传文件 (同步方法，应在线程中运行)
        """
        # 检查文件是否为空
        if not file_obj or not filename:
            raise FileValidationError("文件不能为空", "EMPTY_FILE")
        
        # 检查文件扩展名
        file_ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        
        if not file_ext:
            file_ext = self._detect_file_type_from_content(file_obj)
        
        if file_ext not in settings.ALLOWED_EXTENSIONS:
            raise FileValidationError(
                f"不支持的文件类型: {file_ext}。支持的类型: {', '.join(settings.ALLOWED_EXTENSIONS)}",
                "UNSUPPORTED_FILE_TYPE"
            )
        
        # 检查文件大小
        try:
            file_obj.seek(0, 2)
            file_size = file_obj.tell()
            file_obj.seek(0)
            
            if file_size > settings.MAX_FILE_SIZE:
                raise FileValidationError(
                    f"文件大小超过限制。最大允许: {settings.MAX_FILE_SIZE / (1024*1024):.1f}MB",
                    "FILE_TOO_LARGE"
                )
        except (OSError, AttributeError):
            pass

    def _detect_file_type_from_content(self, file_obj) -> str:
        """从文件内容检测文件类型"""
        try:
            original_position = file_obj.tell()
            file_obj.seek(0)
            header = file_obj.read(16)
            file_obj.seek(original_position)
            
            if not header:
                return ''
            
            if header.startswith(b'\xff\xd8\xff'): return 'jpg'
            if header.startswith(b'\x89PNG\r\n\x1a\n'): return 'png'
            if header.startswith(b'GIF87a') or header.startswith(b'GIF89a'): return 'gif'
            if header.startswith(b'%PDF'): return 'pdf'
            
            try:
                header.decode('utf-8')
                return 'txt'
            except UnicodeDecodeError:
                pass
                
        except Exception:
            pass
        return ''

    def generate_object_name(self, original_filename: str) -> str:
        """生成对象存储名称"""
        file_ext = ''
        if '.' in original_filename:
            file_ext = '.' + original_filename.rsplit('.', 1)[-1].lower()
        
        date_prefix = datetime.now().strftime('%Y/%m/%d')
        unique_id = str(uuid.uuid4())
        return f"{date_prefix}/{unique_id}{file_ext}"

    def _validate_task(self, file_obj, filename: str, object_name: str = None):
        """在线程中执行文件验证和参数准备"""
        # 1. 准备参数
        if object_name is None:
            object_name = self.generate_object_name(filename)
            
        content_type = self._get_content_type(filename)

        # 2. 验证
        self.validate_file(file_obj, filename)
        
        # 验证后重置指针
        file_obj.seek(0, 2)
        file_size = file_obj.tell()
        file_obj.seek(0)
        
        return file_size, object_name, content_type

    def _execute_upload_task(self, file_obj, filename: str, file_size: int, object_name: str, content_type: str):
        """在线程中执行实际上传"""
        client = self.client_manager.get_client()
        return client.put_object(
            bucket_name=self.bucket_name,
            object_name=object_name,
            data=file_obj,
            length=file_size,
            content_type=content_type
        )

    async def upload_file(self, file_obj, filename: str, object_name: str = None, original_url: str = None) -> Dict[str, Any]:
        """
        异步上传文件到 MinIO
        """
        try:
            await self._ensure_bucket()
            
            start_time = datetime.now()
            
            # 1. 验证任务 (CPU/IO Bound)
            # 必须先执行验证，验证通过后才能进行上传
            file_size, object_name, content_type = await self._run_in_thread(
                self._validate_task,
                file_obj,
                filename,
                object_name
            )
            
            # 2. 上传任务 (Network IO Bound)
            result = await self._run_in_thread(
                self._execute_upload_task,
                file_obj,
                filename,
                file_size,
                object_name,
                content_type
            )
            
            duration = (datetime.now() - start_time).total_seconds()
            
            preview_url = await self.generate_preview_url(object_name)
            
            logger.info(f"File uploaded successfully: {filename} -> {object_name} ({duration:.2f}s)")
            
            return {
                'object_name': object_name,
                'original_filename': filename,
                'file_size': file_size,
                'preview_url': preview_url,
                'upload_time': datetime.now().isoformat(),
                'etag': result.etag,
                'original_url': original_url
            }
            
        except FileValidationError:
            raise
        except S3Error as e:
            logger.error(f"MinIO upload error: {e}")
            raise FileUploadError(f"文件上传失败: {str(e)}", "MINIO_UPLOAD_ERROR")
        except Exception as e:
            logger.exception(f"Unexpected upload error: {e}")
            raise FileUploadError(f"文件上传失败: {str(e)}", "UPLOAD_ERROR")

    async def generate_preview_url(self, object_name: str) -> str:
        """生成预览URL"""
        try:
            file_ext = object_name.rsplit('.', 1)[-1].lower() if '.' in object_name else ''
            previewable_types = ['jpg', 'jpeg', 'png', 'gif', 'pdf']
            
            if file_ext not in previewable_types:
                return ''
            
            console_endpoint = settings.MINIO_CONSOLE_ENDPOINT
            protocol = 'https' if settings.MINIO_SECURE else 'http'
            
            encoded_prefix = urllib.parse.quote(object_name, safe='')
            
            # 注意: 这里的 bucket_name 应该使用 settings 中的
            preview_url = (
                f"{protocol}://{console_endpoint}/api/v1/buckets/{self.bucket_name}/objects/download"
                f"?preview=true&prefix={encoded_prefix}&version_id=null"
            )
            return preview_url
            
        except Exception as e:
            logger.error(f"Preview URL generation failed: {e}")
            return ''

    def _stat_task(self, object_name: str):
        """在线程中执行获取文件信息任务"""
        client = self.client_manager.get_client()
        return client.stat_object(self.bucket_name, object_name)

    async def get_file_info(self, object_name: str) -> Dict[str, Any]:
        """异步获取文件信息"""
        try:
            await self._ensure_bucket()
            
            stat = await self._run_in_thread(self._stat_task, object_name)
            
            return {
                'object_name': object_name,
                'size': stat.size,
                'last_modified': stat.last_modified.isoformat(),
                'etag': stat.etag,
                'content_type': stat.content_type
            }
        except S3Error as e:
            if e.code == 'NoSuchKey':
                raise FileDownloadError("文件不存在", "FILE_NOT_FOUND")
            logger.error(f"Get file info failed: {e}")
            raise FileDownloadError(f"获取文件信息失败: {str(e)}", "FILE_INFO_ERROR")
        except Exception as e:
            logger.error(f"Get file info exception: {e}")
            raise FileDownloadError(f"获取文件信息失败: {str(e)}", "FILE_INFO_ERROR")

    def _delete_task(self, object_name: str):
        """在线程中执行删除文件任务"""
        client = self.client_manager.get_client()
        
        # Check existence first
        try:
            client.stat_object(self.bucket_name, object_name)
        except S3Error as e:
            if e.code == 'NoSuchKey':
                raise FileDownloadError("文件不存在", "FILE_NOT_FOUND")
            raise
        
        client.remove_object(self.bucket_name, object_name)

    async def delete_file(self, object_name: str) -> Dict[str, Any]:
        """异步删除文件"""
        try:
            await self._ensure_bucket()
            
            await self._run_in_thread(self._delete_task, object_name)
            
            logger.info(f"File deleted: {object_name}")
            
            return {
                'object_name': object_name,
                'deleted': True,
                'delete_time': datetime.now().isoformat()
            }
        except FileDownloadError:
            raise
        except S3Error as e:
            logger.error(f"MinIO delete error: {e}")
            raise FileDownloadError(f"文件删除失败: {str(e)}", "MINIO_DELETE_ERROR")
        except Exception as e:
            logger.error(f"Delete exception: {e}")
            raise FileDownloadError(f"文件删除失败: {str(e)}", "DELETE_ERROR")

    def _get_content_type(self, filename: str) -> str:
        content_types = {
            'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png',
            'gif': 'image/gif', 'pdf': 'application/pdf', 'doc': 'application/msword',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'xls': 'application/vnd.ms-excel',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'txt': 'text/plain', 'zip': 'application/zip'
        }
        file_ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        return content_types.get(file_ext, 'application/octet-stream')

# Global instance
_minio_service = None

def get_minio_service() -> MinioService:
    global _minio_service
    if _minio_service is None:
        _minio_service = MinioService()
    return _minio_service
