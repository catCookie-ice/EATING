"""Redis 缓存工具"""
import json
import hashlib
import time
from typing import Optional, Any

import redis
from app.config import settings

_redis_client = None
_redis_degraded = False          # Redis 是否已知不可用
_redis_retry_after: float = 0    # 降级状态下尝试重连的时间戳


def get_redis() -> Optional[redis.Redis]:
    """获取 Redis 连接（惰性初始化，降级安全）

    Redis 不可用时自动进入降级模式，60 秒后尝试恢复。
    返回 None 时调用方应跳过缓存操作。
    """
    global _redis_client, _redis_degraded, _redis_retry_after

    # 降级模式：未到重试时间，直接返回 None
    if _redis_degraded and time.time() < _redis_retry_after:
        return None

    if _redis_client is None:
        try:
            _redis_client = redis.Redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=2,   # Redis 不可用时快速失败
                socket_timeout=3,            # 操作超时
                retry_on_timeout=False,
                health_check_interval=30,    # 定期检查连接健康
            )
            # 验证连接是否可用（发送一个 PING）
            _redis_client.ping()
        except Exception:
            _redis_degraded = True
            _redis_retry_after = time.time() + 60
            _redis_client = None
            return None

    # 成功获取连接，退出降级模式
    _redis_degraded = False
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
