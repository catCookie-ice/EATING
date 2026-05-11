"""
DeepSeek AI 工具模块

提供 DeepSeek API 的调用功能，使用 OpenAI 兼容接口
"""

from typing import Any, Optional

from openai import OpenAI
from pydantic import BaseModel

from app.config import settings


# DeepSeek API 配置
DEEPSEEK_API_KEY = settings.DEEPSEEK_API_KEY or ""
DEEPSEEK_MODEL = settings.DEEPSEEK_MODEL or "deepseek-chat"

# 惰性初始化客户端
_client: Optional[OpenAI] = None


def get_client() -> OpenAI:
    """获取 OpenAI 客户端（惰性初始化）"""
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com",
        )
    return _client


class DeepSeekResponse(BaseModel):
    """DeepSeek 响应模型"""
    content: str
    model: str
    usage: dict = {}


def chat(
    messages: list[dict[str, str]],
    model: str = DEEPSEEK_MODEL,
    temperature: float = 0.7,
    max_tokens: int = 2048,
    stream: bool = False,
) -> Any:
    """
    调用 DeepSeek chat 接口

    Args:
        messages: 消息列表，格式 [{"role": "user", "content": "..."}, ...]
        model: 使用的模型，默认 deepseek-chat
        temperature: 温度参数，控制随机性，0-2
        max_tokens: 最大生成 token 数
        stream: 是否使用流式输出

    Returns:
        DeepSeekResponse 或 StreamingResponse
    """
    if not DEEPSEEK_API_KEY:
        raise ValueError("DEEPSEEK_API_KEY 未配置，请在 .env 中设置")

    if stream:
        return get_client().chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )

    response = get_client().chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    content = response.choices[0].message.content

    return DeepSeekResponse(
        content=content,
        model=response.model,
        usage={
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        },
    )


def simple_chat(
    prompt: str,
    system_prompt: str = "你是一个有帮助的助手。",
    **kwargs: Any,
) -> str:
    """
    简化的单轮对话接口

    Args:
        user_prompt: 用户输入
        system_prompt: 系统提示词
        **kwargs: 传递给 chat 的其他参数

    Returns:
        AI 回复内容
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]
    result = chat(messages, **kwargs)
    return result.content