"""Redis 缓存工具"""
import json
import hashlib
from typing import Optional, Any

import redis
from app.config import settings

_redis_client = None


def get_redis() -> redis.Redis:
    """获取 Redis 连接（惰性初始化）"""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
        )
    return _redis_client


def make_cache_key(prefix: str, **params) -> str:
    """生成统一的缓存 key

    将参数排序后做 MD5 哈希，确保相同参数生成相同 key。
    None 值的参数会被忽略，避免干扰。

    Args:
        prefix: key 前缀，如 "recipes:list"
        **params: 查询参数键值对

    Returns:
        完整的缓存 key，如 "recipes:list:a1b2c3d4..."
    """
    filtered = {k: v for k, v in params.items() if v is not None}
    key_str = json.dumps(filtered, sort_keys=True)
    hash_val = hashlib.md5(key_str.encode()).hexdigest()
    return f"{prefix}:{hash_val}"


def get_cache(cache_key: str) -> Optional[Any]:
    """获取缓存数据

    Args:
        cache_key: 缓存 key

    Returns:
        解析后的 Python 对象，缓存不存在或异常时返回 None
    """
    try:
        r = get_redis()
        data = r.get(cache_key)
        if data:
            return json.loads(data)
    except Exception:
        pass
    return None


def set_cache(cache_key: str, data: Any, ttl: int = 300):
    """写入缓存

    Args:
        cache_key: 缓存 key
        data: 可 JSON 序列化的 Python 对象
        ttl: 过期时间（秒），默认 300 秒
    """
    try:
        r = get_redis()
        r.setex(cache_key, ttl, json.dumps(data, default=str))
    except Exception:
        pass


def delete_cache_pattern(pattern: str):
    """按通配符模式删除缓存

    Args:
        pattern: Redis 通配符模式，如 "recipes:list:*"
    """
    try:
        r = get_redis()
        keys = r.keys(pattern)
        if keys:
            r.delete(*keys)
    except Exception:
        pass


def blacklist_token(token: str, ttl: int):
    """将token加入黑名单（token将立即失效）

    Args:
        token: JWT token 字符串
        ttl: 黑名单有效期（秒），建议设为token剩余有效期
    """
    try:
        r = get_redis()
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        key = f"token:blacklist:{token_hash}"
        r.setex(key, ttl, "1")
    except Exception:
        pass


def is_token_blacklisted(token: str) -> bool:
    """检查token是否在黑名单中

    Args:
        token: JWT token 字符串

    Returns:
        True=已拉黑，False=正常（Redis不可用时返回False）
    """
    try:
        r = get_redis()
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        key = f"token:blacklist:{token_hash}"
        return r.exists(key) > 0
    except Exception:
        return False
