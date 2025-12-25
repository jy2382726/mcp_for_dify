import urllib3
from minio import Minio
from minio.error import S3Error
from app.core.config import get_settings
from app.core.logger import logger

settings = get_settings()

class MinioClientManager:
    """
    MinIO 客户端连接管理器
    
    实现连接池管理、懒加载、健康检查等功能。
    """
    _instance = None
    _client = None
    _pool_manager = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MinioClientManager, cls).__new__(cls)
        return cls._instance

    def _init_pool(self):
        """初始化连接池"""
        if self._pool_manager is None:
            logger.info(f"Initializing MinIO connection pool with max_size={settings.MINIO_POOL_MAX_SIZE}")
            self._pool_manager = urllib3.PoolManager(
                num_pools=10,
                maxsize=settings.MINIO_POOL_MAX_SIZE,
                timeout=urllib3.Timeout(connect=settings.MINIO_CONNECT_TIMEOUT, read=30.0),
                retries=urllib3.Retry(
                    total=3,
                    backoff_factor=0.2,
                    status_forcelist=[500, 502, 503, 504]
                )
            )

    def get_client(self) -> Minio:
        """
        获取 MinIO 客户端实例（懒加载）
        注意：此方法不再执行网络检查，确保非阻塞。
        """
        if self._client is None:
            self._init_pool()
            logger.info(f"Creating MinIO client for endpoint: {settings.MINIO_ENDPOINT}")
            self._client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE,
                http_client=self._pool_manager
            )
        return self._client

    def ensure_bucket_exists(self):
        """确保配置的 Bucket 存在（同步阻塞方法，应在线程中调用）"""
        try:
            if self._client is None:
                self.get_client()
                
            if not self._client.bucket_exists(settings.MINIO_BUCKET_NAME):
                logger.info(f"Bucket '{settings.MINIO_BUCKET_NAME}' does not exist. Creating it.")
                self._client.make_bucket(settings.MINIO_BUCKET_NAME)
            else:
                logger.debug(f"Bucket '{settings.MINIO_BUCKET_NAME}' exists.")
        except Exception as e:
            logger.error(f"Failed to check/create bucket: {e}")
            # 允许抛出异常以便调用者处理
            raise
            
    def health_check(self) -> bool:
        """
        连接健康检查
        """
        try:
            client = self.get_client()
            # 使用 list_buckets 作为轻量级健康检查
            client.list_buckets()
            return True
        except Exception as e:
            logger.error(f"MinIO health check failed: {e}")
            return False

# 全局单例
minio_client_manager = MinioClientManager()

def get_minio_client() -> MinioClientManager:
    return minio_client_manager
