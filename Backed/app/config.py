from pydantic_settings import BaseSettings
from typing import Optional, List
from enum import Enum


class StorageType(str, Enum):
    """存储类型枚举"""
    CLOUD = "cloud"      # 云存储
    LOCAL = "local"      # 本地存储
    MIXED = "mixed"      # 混合存储


class Settings(BaseSettings):
    model_config = {"extra": "ignore", "env_file": ".env", "env_file_encoding": "utf-8"}

    # Database
    DATABASE_URL: str = "mysql+pymysql://root:password@localhost:3306/eating"

    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # 0级管理员配置
    ADMIN_0_ACCOUNT: str = "a7s90001"
    ADMIN_0_PASSWORD: str = "admin0000"# 注意，请务必牢记最高管理员的密码

    # 存储配置
    STORAGE_TYPE: StorageType = StorageType.LOCAL  # 存储类型：cloud/local/mixed
    # 腾讯云COS配置
    COS_SECRET_ID: Optional[str] = None  # 腾讯云SecretId
    COS_SECRET_KEY: Optional[str] = None  # 腾讯云SecretKey
    COS_BUCKET: Optional[str] = None  # COS桶名称
    COS_REGION: Optional[str] = None  # COS区域
    COS_URL_EXPIRE_SECONDS: int = 3600  # 云存储URL过期时间(秒)
    # 本地存储配置
    LOCAL_UPLOAD_DIR: str = "uploads"  # 本地上传目录
    LOCAL_BASE_URL: str = "/uploads"  # 本地存储基础URL

    # 食材类别枚举
    INGREDIENT_CATEGORIES: List[str] = ["肉", "蛋", "蔬菜", "水果","奶制品","谷物",'豆类', '坚果',"海鲜","其他"]

    # 菜系列表
    CUISINES: List[str] = [
        "川菜", "粤菜", "湘菜", "鲁菜", "苏菜", "浙菜", "闽菜", "徽菜",
        "东北菜", "西北菜","家常菜","西餐", "日料", "韩餐", "东南亚菜","其他"
    ]

    # 烹饪方式列表
    METHODS: List[str] = ["蒸", "煮", "炸", "炒", "焖", "拌", "卤", "烤", "煎", "腌","炖", "其他"]

    # DeepSeek AI 配置
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_MODEL: str = "deepseek-chat"

    # Redis 配置
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL_RECIPES: int = 300  # 食谱列表缓存时间（秒）
    REDIS_CACHE_TTL_INGREDIENTS: int = 600  # 食材列表缓存时间（秒）

    # SMTP 邮件配置
    SMTP_SERVER: str = "smtp.163.com"
    SMTP_PORT: int = 465
    SMTP_USER: str = "catcookie2026@163.com"
    SMTP_PASSWORD: str = "QTPLh37Dq7kRethn"

    # RAG / 向量检索 配置
    EMBEDDING_MODEL: str = "shibing624/text2vec-base-chinese"  # 嵌入模型名称
    RAG_TOP_K: int = 5              # 默认检索返回记录数
    RAG_SIMILARITY_THRESHOLD: float = 0.3  # 相似度阈值
    KB_UPLOAD_DIR: str = "knowledge_bases"  # 上传的知识库存放目录（相对于 resource/）
    KB_DEFAULT_FILE: str = "常见疾病与对应忌口.txt"  # 默认知识库文件

settings = Settings()