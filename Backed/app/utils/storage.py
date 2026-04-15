"""存储工具模块

支持三种存储方式：
- 云存储(Cloud): 腾讯云COS
- 本地存储(Local): 本地文件系统
- 混合存储(Mixed): 优先云存储，云存储失败则使用本地存储

混合存储查找逻辑：优先在云上查找，如果没有则查找本地
"""
import os
import uuid
import shutil
from typing import Optional, Tuple
from datetime import datetime
from pathlib import Path

from app.config import settings, StorageType


class StorageService:
    """存储服务基类"""

    def upload(self, file_data: bytes, filename: str) -> str:
        """上传文件，返回URL"""
        raise NotImplementedError

    def get_url(self, file_path: str) -> str:
        """获取文件访问URL"""
        raise NotImplementedError

    def exists(self, file_path: str) -> bool:
        """检查文件是否存在"""
        raise NotImplementedError

    def delete(self, file_path: str) -> bool:
        """删除文件"""
        raise NotImplementedError


class LocalStorage(StorageService):
    """本地存储服务"""

    def __init__(self):
        self.base_dir = Path(settings.LOCAL_UPLOAD_DIR)
        self.base_url = settings.LOCAL_BASE_URL
        # 确保上传目录存在
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, filename: str) -> Path:
        """生成唯一文件路径"""
        # 按日期组织文件
        date_str = datetime.now().strftime("%Y%m%d")
        file_dir = self.base_dir / date_str
        file_dir.mkdir(parents=True, exist_ok=True)

        # 生成唯一文件名
        ext = Path(filename).suffix
        unique_name = f"{uuid.uuid4().hex}{ext}"
        return file_dir / unique_name

    def upload(self, file_data: bytes, filename: str) -> str:
        """上传文件到本地存储"""
        file_path = self._get_file_path(filename)

        with open(file_path, "wb") as f:
            f.write(file_data)

        # 返回相对URL路径
        relative_path = str(file_path.relative_to(self.base_dir))
        return f"{self.base_url}/{relative_path}"

    def get_url(self, file_path: str) -> str:
        """获取本地文件访问URL"""
        # file_path 已经是相对URL路径
        return file_path

    def exists(self, file_path: str) -> bool:
        """检查本地文件是否存在"""
        if file_path.startswith(self.base_url):
            relative_path = file_path[len(self.base_url):].lstrip("/")
            full_path = self.base_dir / relative_path
        else:
            full_path = self.base_dir / file_path
        return full_path.exists()

    def delete(self, file_path: str) -> bool:
        """删除本地文件"""
        try:
            if file_path.startswith(self.base_url):
                relative_path = file_path[len(self.base_url):].lstrip("/")
                full_path = self.base_dir / relative_path
            else:
                full_path = self.base_dir / file_path

            if full_path.exists():
                full_path.unlink()
                return True
            return False
        except Exception:
            return False

    def find_file(self, file_path: str) -> Optional[str]:
        """查找文件，返回实际存在的URL"""
        if self.exists(file_path):
            return self.get_url(file_path)
        return None


class CloudStorage(StorageService):
    """云存储服务 (腾讯云COS)"""

    def __init__(self):
        from qcloud_cos_v5 import CosConfig, CosS3Client
        import logging

        # 禁用腾讯云SDK日志
        logging.getLogger("qcloud_cos_v5").setLevel(logging.ERROR)

        if not all([settings.COS_SECRET_ID, settings.COS_SECRET_KEY, settings.COS_BUCKET, settings.COS_REGION]):
            raise ValueError("云存储配置不完整，需要设置 COS_SECRET_ID, COS_SECRET_KEY, COS_BUCKET, COS_REGION")

        # 配置COS客户端
        config = CosConfig(
            SecretId=settings.COS_SECRET_ID,
            SecretKey=settings.COS_SECRET_KEY,
            Region=settings.COS_REGION
        )
        self.client = CosS3Client(config)
        self.bucket = settings.COS_BUCKET

    def _get_key(self, filename: str) -> str:
        """生成COS对象键"""
        date_str = datetime.now().strftime("%Y%m%d")
        ext = Path(filename).suffix
        unique_name = f"{uuid.uuid4().hex}{ext}"
        return f"{date_str}/{unique_name}"

    def upload(self, file_data: bytes, filename: str) -> str:
        """上传文件到云存储"""
        key = self._get_key(filename)

        from io import BytesIO
        file_stream = BytesIO(file_data)

        self.client.put_object(
            Bucket=self.bucket,
            Body=file_stream,
            Key=key,
            ContentType=self._get_content_type(filename)
        )

        # 返回云存储的URL (使用永久URL或临时URL)
        return self.get_url(key)

    def get_url(self, file_path: str) -> str:
        """获取云存储文件访问URL"""
        # 返回永久URL
        return f"https://{self.bucket}.cos.{settings.COS_REGION}.myqcloud.com/{file_path}"

    def exists(self, file_path: str) -> bool:
        """检查云存储文件是否存在"""
        try:
            self.client.head_object(
                Bucket=self.bucket,
                Key=file_path
            )
            return True
        except Exception:
            return False

    def delete(self, file_path: str) -> bool:
        """删除云存储文件"""
        try:
            self.client.delete_object(
                Bucket=self.bucket,
                Key=file_path
            )
            return True
        except Exception:
            return False

    def find_file(self, file_path: str) -> Optional[str]:
        """查找文件，返回实际存在的URL"""
        if self.exists(file_path):
            return self.get_url(file_path)
        return None

    def _get_content_type(self, filename: str) -> str:
        """根据文件扩展名获取Content-Type"""
        ext = Path(filename).suffix.lower()
        content_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".bmp": "image/bmp",
            ".svg": "image/svg+xml",
        }
        return content_types.get(ext, "application/octet-stream")


class MixedStorage(StorageService):
    """混合存储服务

    上传时：优先尝试云存储，如果失败则使用本地存储
    查找时：优先在云上查找，如果不存在则查找本地
    """

    def __init__(self):
        self._cloud = None
        self._local = None

    @property
    def cloud(self):
        """延迟初始化云存储"""
        if self._cloud is None:
            self._cloud = CloudStorage()
        return self._cloud

    @property
    def local(self):
        """延迟初始化本地存储"""
        if self._local is None:
            self._local = LocalStorage()
        return self._local

    def upload(self, file_data: bytes, filename: str) -> str:
        """混合存储上传 - 优先云存储"""
        try:
            # 尝试云存储
            url = self.cloud.upload(file_data, filename)
            return url
        except Exception as e:
            # 云存储失败，使用本地存储
            import logging
            logging.warning(f"云存储上传失败，切换到本地存储: {e}")
            return self.local.upload(file_data, filename)

    def get_url(self, file_path: str) -> str:
        """获取文件访问URL"""
        # 尝试云存储URL
        if file_path.startswith("http://") or file_path.startswith("https://"):
            return file_path
        return self.cloud.get_url(file_path)

    def exists(self, file_path: str) -> bool:
        """检查文件是否存在 - 优先查云，再查本地"""
        # 如果是本地URL路径，先检查本地
        if file_path.startswith(settings.LOCAL_BASE_URL):
            if self.local.exists(file_path):
                return True
            return False

        # 尝试云存储
        if self.cloud.exists(file_path):
            return True

        # 云上没有，检查本地
        # 可能是相对路径，尝试本地
        return self.local.exists(file_path)

    def find_file(self, file_path: str) -> Optional[str]:
        """查找文件，返回实际存在的URL

        混合存储查找逻辑：
        1. 先尝试云存储
        2. 如果云上没有，检查本地存储
        3. 返回实际存在的URL，如果都不存在返回None
        """
        from app.config import settings as app_settings

        # 如果是完整的URL，检查其来源
        if file_path.startswith("http://") or file_path.startswith("https://"):
            # 检查是否是本地URL
            if app_settings.LOCAL_BASE_URL in file_path:
                if self.local.exists(file_path):
                    return file_path
                return None

            # 云URL，提取key尝试
            # 尝试从URL提取bucket
            for bucket_name in [self.cloud.bucket, app_settings.COS_BUCKET]:
                if bucket_name and bucket_name in file_path:
                    # 提取key
                    try:
                        key = file_path.split(f"{bucket_name}.cos.")[-1]
                        if "/" in key:
                            key = key.split("/", 1)[1]

                        if self.cloud.exists(key):
                            return self.cloud.get_url(key)
                    except Exception:
                        pass
                    break
            return None

        # 如果是相对路径或云key
        # 先尝试云存储
        if self.cloud.exists(file_path):
            return self.cloud.get_url(file_path)

        # 再尝试本地存储
        if self.local.exists(file_path):
            return self.local.get_url(file_path)

        return None

    def delete(self, file_path: str) -> bool:
        """删除文件 - 云和本地都尝试删除"""
        cloud_result = self.cloud.delete(file_path)
        local_result = self.local.delete(file_path)
        return cloud_result or local_result


# 获取存储服务实例
def get_storage_service() -> StorageService:
    """获取存储服务实例"""
    if settings.STORAGE_TYPE == StorageType.CLOUD:
        return CloudStorage()
    elif settings.STORAGE_TYPE == StorageType.LOCAL:
        return LocalStorage()
    elif settings.STORAGE_TYPE == StorageType.MIXED:
        return MixedStorage()
    else:
        raise ValueError(f"不支持的存储类型: {settings.STORAGE_TYPE}")


# 全局存储服务实例
_storage_service: Optional[StorageService] = None


def get_storage() -> StorageService:
    """获取全局存储服务实例"""
    global _storage_service
    if _storage_service is None:
        _storage_service = get_storage_service()
    return _storage_service
