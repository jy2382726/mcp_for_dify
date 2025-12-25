# -*- coding: utf-8 -*-
"""
文件服务核心模块

提供文件上传、下载、预览URL生成等核心业务逻辑。
"""

import uuid
from datetime import datetime

# 尝试导入S3Error
from minio.error import S3Error

from .minio_client import get_minio_client
from app.config import Config
from app.exceptions import FileUploadError, FileDownloadError, FileValidationError
import logging


class FileService:
    """
    文件服务类
    
    提供文件的上传、下载、预览等核心功能。
    """
    
    def __init__(self):
        """
        初始化文件服务
        """
        self.minio_client = get_minio_client()
        self.bucket_name = self.minio_client.get_bucket_name()
    
    def validate_file(self, file_obj, filename):
        """
        验证上传文件
        
        Args:
            file_obj: 文件对象
            filename (str): 文件名
            
        Raises:
            FileValidationError: 文件验证失败时抛出
        """
        # 检查文件是否为空
        if not file_obj or not filename:
            raise FileValidationError("文件不能为空", "EMPTY_FILE")
        
        # 检查文件扩展名
        file_ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        
        # 如果文件扩展名为空，尝试从文件内容检测类型
        # 2025-10-17 新增：从文件内容检测文件类型，解决文件名无法获取扩展名从而不能正确校验文件类型的问题
        if not file_ext:
            file_ext = self._detect_file_type_from_content(file_obj)
        
        if file_ext not in Config.ALLOWED_EXTENSIONS:
            raise FileValidationError(
                f"不支持的文件类型: {file_ext}。支持的类型: {', '.join(Config.ALLOWED_EXTENSIONS)}",
                "UNSUPPORTED_FILE_TYPE"
            )
        
        # 检查文件大小（如果可以获取）
        try:
            file_obj.seek(0, 2)  # 移动到文件末尾
            file_size = file_obj.tell()
            file_obj.seek(0)  # 重置到文件开头
            
            if file_size > Config.MAX_FILE_SIZE:
                raise FileValidationError(
                    f"文件大小超过限制。最大允许: {Config.MAX_FILE_SIZE / (1024*1024):.1f}MB",
                    "FILE_TOO_LARGE"
                )
        except (OSError, AttributeError):
            # 如果无法获取文件大小，跳过大小检查
            pass
    
    # 2025-10-17 新增：从文件内容检测文件类型，解决文件名无法获取扩展名从而不能正确校验文件类型的问题
    def _detect_file_type_from_content(self, file_obj):
        """
        从文件内容检测文件类型
        
        Args:
            file_obj: 文件对象
            
        Returns:
            str: 检测到的文件扩展名，如果无法检测则返回空字符串
        """
        try:
            # 保存当前位置
            original_position = file_obj.tell()
            
            # 读取文件头部字节用于检测
            file_obj.seek(0)
            header = file_obj.read(16)
            
            # 恢复文件位置
            file_obj.seek(original_position)
            
            if not header:
                return ''
            
            # 检测常见的文件类型签名
            # JPEG: FF D8 FF
            if header.startswith(b'\xff\xd8\xff'):
                return 'jpg'
            
            # PNG: 89 50 4E 47 0D 0A 1A 0A
            if header.startswith(b'\x89PNG\r\n\x1a\n'):
                return 'png'
            
            # GIF: GIF87a or GIF89a
            if header.startswith(b'GIF87a') or header.startswith(b'GIF89a'):
                return 'gif'
            
            # PDF: %PDF
            if header.startswith(b'%PDF'):
                return 'pdf'
            
            # 纯文本文件检测（尝试解码为UTF-8）
            try:
                header.decode('utf-8')
                # 如果能够解码为UTF-8，可能是文本文件
                return 'txt'
            except UnicodeDecodeError:
                pass
                
        except (OSError, AttributeError, Exception):
            # 如果检测过程中出现错误，返回空字符串
            pass
        
        return ''
    
    def generate_object_name(self, original_filename):
        """
        生成对象存储名称
        
        Args:
            original_filename (str): 原始文件名
            对原始文件名做以下处理：
            1. 增加当前日期的时间戳（格式：YYYY/MM/DD）
            2. 修改文件名为UUID（32位）
            
        Returns:
            str: 生成的对象名称
        """
        # 获取文件扩展名
        file_ext = ''
        if '.' in original_filename:
            file_ext = '.' + original_filename.rsplit('.', 1)[-1].lower()
        
        # 生成唯一文件名：日期/UUID.扩展名
        date_prefix = datetime.now().strftime('%Y/%m/%d')
        unique_id = str(uuid.uuid4())
        object_name = f"{date_prefix}/{unique_id}{file_ext}"
        
        return object_name
        # 直接使用传入的对象名称，不做任何修改
        # return original_filename
    
    def upload_file(self, file_obj, filename, object_name=None, original_url=None):
        """
        上传文件到MinIO
        
        Args:
            file_obj: 文件对象
            filename (str): 原始文件名
            object_name (str, optional): 对象名称。如果未提供，将使用原始文件名生成
            original_url (str, optional): 文件原始URL地址
            
        Returns:
            dict: 上传结果，包含文件信息和预览URL
            
        Raises:
            FileUploadError: 上传失败时抛出
        """
        try:
            # 验证文件
            self.validate_file(file_obj, filename)
            
            # 如果未提供对象名称，则使用原始文件名生成
            if object_name is None:
                object_name = self.generate_object_name(filename)
            
            # 获取文件大小
            file_obj.seek(0, 2)
            file_size = file_obj.tell()
            file_obj.seek(0)
            
            # 上传文件
            client = self.minio_client.get_client()
            result = client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                data=file_obj,
                length=file_size,
                content_type=self._get_content_type(filename)
            )
            
            # 生成预览URL
            preview_url = self.generate_preview_url(object_name)
            
            # 记录上传日志
            logging.info(f"文件上传成功: {filename} -> {object_name}")
            
            return {
                'object_name': object_name,
                'original_filename': filename,
                'file_size': file_size,
                'preview_url': preview_url,
                'upload_time': datetime.now().isoformat(),
                # etag是文件的唯一标识符，用于验证文件完整性，由MinIO在上传时生成
                'etag': result.etag,
                # 添加文件原始URL地址
                'original_url': original_url
            }
            
        except FileValidationError:
            raise
        except S3Error as e:
            logging.error(f"MinIO上传错误: {str(e)}")
            raise FileUploadError(f"文件上传失败: {str(e)}", "MINIO_UPLOAD_ERROR")
        except Exception as e:
            logging.error(f"文件上传异常: {str(e)}")
            raise FileUploadError(f"文件上传失败: {str(e)}", "UPLOAD_ERROR")
    
    def generate_preview_url(self, object_name, expiry_seconds=None):
        """
        生成文件预览URL
        
        Args:
            object_name (str): 对象名称
            expiry_seconds (int): URL有效期（秒），此参数已废弃
            
        Returns:
            str: 预览URL，图片和PDF返回MinIO Console预览地址，其他文件返回空字符串
            
        Raises:
            FileDownloadError: 生成URL失败时抛出
        """
        try:
            # 从object_name中提取文件扩展名
            file_ext = ''
            if '.' in object_name:
                file_ext = object_name.rsplit('.', 1)[-1].lower()
            
            # 定义可预览的文件类型
            previewable_types = ['jpg', 'jpeg', 'png', 'gif', 'pdf']
            
            # 如果不是可预览的文件类型，返回空字符串
            if file_ext not in previewable_types:
                return ''
            
            # 构建MinIO Console预览URL
            # 格式: http://localhost:19000/api/v1/buckets/{bucket}/objects/download?preview=true&prefix={object_name}&version_id=null
            
            # 获取MinIO Console端点配置
            console_endpoint = Config.MINIO_CONSOLE_ENDPOINT
            
            # 构建协议前缀
            protocol = 'https' if Config.MINIO_SECURE else 'http'
            
            # URL编码文件名
            import urllib.parse
            encoded_prefix = urllib.parse.quote(object_name, safe='')
            
            # 构建完整的预览URL
            preview_url = (
                f"{protocol}://{console_endpoint}/api/v1/buckets/{self.bucket_name}/objects/download"
                f"?preview=true&prefix={encoded_prefix}&version_id=null"
            )
            
            return preview_url
            
        except Exception as e:
            logging.error(f"预览URL生成异常: {str(e)}")
            raise FileDownloadError(f"生成预览URL失败: {str(e)}", "PREVIEW_URL_ERROR")
    
    def get_file_info(self, object_name):
        """
        获取文件信息
        
        Args:
            object_name (str): 对象名称
            
        Returns:
            dict: 文件信息
            
        Raises:
            FileDownloadError: 获取文件信息失败时抛出
        """
        try:
            client = self.minio_client.get_client()
            stat = client.stat_object(self.bucket_name, object_name)
            
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
            logging.error(f"获取文件信息失败: {str(e)}")
            raise FileDownloadError(f"获取文件信息失败: {str(e)}", "FILE_INFO_ERROR")
        except Exception as e:
            logging.error(f"文件信息获取异常: {str(e)}")
            raise FileDownloadError(f"获取文件信息失败: {str(e)}", "FILE_INFO_ERROR")
    
    def delete_file(self, object_name):
        """
        删除文件
        
        Args:
            object_name (str): 对象名称
            
        Returns:
            dict: 删除结果
            
        Raises:
            FileDownloadError: 删除失败时抛出
        """
        try:
            client = self.minio_client.get_client()
            
            # 先检查文件是否存在
            try:
                client.stat_object(self.bucket_name, object_name)
            except S3Error as e:
                if e.code == 'NoSuchKey':
                    raise FileDownloadError("文件不存在", "FILE_NOT_FOUND")
                raise
            
            # 执行删除操作
            client.remove_object(self.bucket_name, object_name)
            
            # 记录删除日志
            logging.info(f"文件删除成功: {object_name}")
            
            return {
                'object_name': object_name,
                'deleted': True,
                'delete_time': datetime.now().isoformat()
            }
            
        except FileDownloadError:
            raise
        except S3Error as e:
            logging.error(f"MinIO删除错误: {str(e)}")
            raise FileDownloadError(f"文件删除失败: {str(e)}", "MINIO_DELETE_ERROR")
        except Exception as e:
            logging.error(f"文件删除异常: {str(e)}")
            raise FileDownloadError(f"文件删除失败: {str(e)}", "DELETE_ERROR")

    def _get_content_type(self, filename):
        """
        根据文件名获取Content-Type
        
        Args:
            filename (str): 文件名
            
        Returns:
            str: Content-Type
        """
        content_types = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'pdf': 'application/pdf',
            'doc': 'application/msword',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'xls': 'application/vnd.ms-excel',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'txt': 'text/plain',
            'zip': 'application/zip'
        }
        
        file_ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        return content_types.get(file_ext, 'application/octet-stream')


# 全局文件服务实例
_file_service = None


def get_file_service():
    """
    获取全局文件服务实例（单例模式）
    
    Returns:
        FileService: 文件服务实例
    """
    global _file_service
    if _file_service is None:
        _file_service = FileService()
    return _file_service