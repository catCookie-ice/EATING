"""
AI 聊天路由

提供与 DeepSeek AI 的流式对话接口
"""

from typing import AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from openai import OpenAI

from app.dependencies import get_current_user
from app.config import settings

router = APIRouter(prefix="/chat", tags=["AI 聊天"])


class ChatRequest(BaseModel):
    """聊天请求"""
    messages: list[dict[str, str]]
    temperature: float = 0.7
    max_tokens: int = 2048


class ChatMessage(BaseModel):
    """单条消息"""
    role: str
    content: str


@router.post("/")
async def chat(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
) -> StreamingResponse:
    """
    流式对话接口

    接收消息列表，返回流式响应
    """
    if not settings.DEEPSEEK_API_KEY:
        return StreamingResponse(
            iter(["抱歉，AI 服务未配置，请在环境变量中设置 DEEPSEEK_API_KEY"]),
            media_type="text/event-stream",
        )

    client = OpenAI(
        api_key=settings.DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com",
    )

    async def generate() -> AsyncGenerator[str, None]:
        try:
            stream = client.chat.completions.create(
                model=settings.DEEPSEEK_MODEL,
                messages=request.messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stream=True,
            )

            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    yield f"data: {content}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            yield f"data: 抱歉，服务出错: {str(e)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )