"""
AI 聊天路由

提供与 DeepSeek AI 的流式对话接口，集成推荐 skill 作为可调用工具
"""

import difflib
import json
from typing import AsyncGenerator, List, Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from openai import OpenAI
from sqlalchemy.orm import Session

from app.dependencies import get_current_user
from app.config import settings
from app.database import get_db
from app.models.person import Person
from app.models.user import User
from app.models.recipe import Recipe
from app.schemas.recipe import RecipeStatus

router = APIRouter(prefix="/chat", tags=["AI 聊天"])


class ChatRequest(BaseModel):
    """聊天请求"""
    messages: list[dict[str, str]]
    temperature: float = 0.7
    max_tokens: int = 2048


# ===== 工具定义 =====

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "recommend_recipes",
            "description": "根据用户的口味偏好、浏览记录和收藏记录，综合计算口味占比，推荐最匹配且不含用户过敏源的食谱。用户可补充菜系、排除食材、口味调整等要求",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "返回的推荐食谱数量，最多20条",
                        "default": 10
                    },
                    "cuisine": {
                        "type": "string",
                        "description": "筛选特定菜系，如：川菜、粤菜、湘菜、鲁菜、东北菜、家常菜、西餐等。不传则不限菜系"
                    },
                    "exclude_ingredients": {
                        "type": "string",
                        "description": "要排除的食材名称，多个用中文逗号或英文逗号分隔，如：鸡蛋,花生,虾"
                    },
                    "taste_adjustments": {
                        "type": "object",
                        "description": "口味微调：在综合口味基础上调整某些味道的权重。如用户说'不要太甜'则 sweet 传 decrease，'要更辣'则 spicy 传 increase",
                        "properties": {
                            "sour": {"type": "string", "enum": ["increase", "decrease"], "description": "酸味"},
                            "sweet": {"type": "string", "enum": ["increase", "decrease"], "description": "甜味"},
                            "bitter": {"type": "string", "enum": ["increase", "decrease"], "description": "苦味"},
                            "spicy": {"type": "string", "enum": ["increase", "decrease"], "description": "辣味"},
                            "salty": {"type": "string", "enum": ["increase", "decrease"], "description": "咸味"}
                        }
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_recipe_info",
            "description": "查询某个食谱的详细信息，包括所需材料、制作步骤、调料、营养成分、过敏源等。当用户问'某道菜怎么做'、'需要什么材料'、'步骤是什么'时使用此工具",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "食谱名称，支持模糊匹配，如：番茄炒鸡蛋、红烧肉、麻婆豆腐"
                    }
                },
                "required": ["name"]
            }
        }
    }
]

# 口味维度
TASTE_DIMS = ["sour", "sweet", "bitter", "spicy", "salty"]
DEFAULT_TASTE = {d: 0.2 for d in TASTE_DIMS}
WEIGHT_PERSONAL = 0.5
WEIGHT_FAVORITES = 0.3
WEIGHT_BROWSE = 0.2


def _get_taste(v: Optional[dict]) -> dict:
    """安全获取口味向量"""
    if not v or not isinstance(v, dict):
        return dict(DEFAULT_TASTE)
    return {d: float(v.get(d, 0.2)) for d in TASTE_DIMS}


def _cosine_similarity(a: dict, b: dict) -> float:
    """余弦相似度"""
    va = [a.get(d, 0) for d in TASTE_DIMS]
    vb = [b.get(d, 0) for d in TASTE_DIMS]
    dot = sum(x * y for x, y in zip(va, vb))
    na = sum(x * x for x in va) ** 0.5
    nb = sum(y * y for y in vb) ** 0.5
    return dot / (na * nb) if na and nb else 0.0


def _execute_recommendation(
    account: str, db: Session, limit: int = 10,
    cuisine: Optional[str] = None,
    exclude_ingredients: Optional[str] = None,
    taste_adjustments: Optional[dict] = None,
) -> dict:
    """执行推荐逻辑（被 AI tool call 调用）

    Args:
        account: 用户账户
        db: 数据库会话
        limit: 返回上限
        cuisine: 筛选菜系
        exclude_ingredients: 排除的食材（逗号分隔）
        taste_adjustments: 口味微调 {"sweet": "decrease", "spicy": "increase"}

    Returns:
        推荐结果字典
    """
    user = db.query(User).filter(User.account == account).first()
    if not user:
        return {"error": "用户信息不存在"}

    limit = min(limit, 20)

    # 1. 个人口味
    personal = _get_taste(user.taste)

    # 2. 收藏食谱口味
    fav_tastes: List[dict] = []
    for fav in (user.favorite_records or [])[:30]:
        rid = fav.get("recipe_id")
        if rid:
            r = db.query(Recipe).filter(Recipe.id == rid, Recipe.is_delete == False).first()
            if r and r.taste:
                fav_tastes.append(_get_taste(r.taste))

    # 3. 浏览记录口味
    browse_tastes: List[dict] = []
    for entry in (user.browse_history or [])[:50]:
        rid = entry.get("recipe_id")
        if rid:
            r = db.query(Recipe).filter(Recipe.id == rid, Recipe.is_delete == False).first()
            if r and r.taste:
                browse_tastes.append(_get_taste(r.taste))

    # 4. 加权综合口味
    target = {}
    for d in TASTE_DIMS:
        pv = personal.get(d, 0.2) * WEIGHT_PERSONAL
        fav_avg = sum(t.get(d, 0.2) for t in fav_tastes) / len(fav_tastes) if fav_tastes else 0.2
        browse_avg = sum(t.get(d, 0.2) for t in browse_tastes) / len(browse_tastes) if browse_tastes else 0.2
        target[d] = pv + fav_avg * WEIGHT_FAVORITES + browse_avg * WEIGHT_BROWSE

    # 4.5 应用口味微调
    if taste_adjustments:
        for d, adj in taste_adjustments.items():
            if d in TASTE_DIMS:
                if adj == "increase":
                    target[d] *= 1.5
                elif adj == "decrease":
                    target[d] *= 0.5
        # 重新归一化
        total = sum(target.values())
        if total > 0:
            for d in TASTE_DIMS:
                target[d] = round(target[d] / total, 4)

    # 5. 查询公开食谱
    user_allergens = set(user.allergens or [])
    query = db.query(Recipe).filter(
        Recipe.is_delete == False,
        Recipe.status == RecipeStatus.PUBLIC,
    )
    if cuisine:
        query = query.filter(Recipe.cuisine == cuisine)
    recipes = query.all()

    # 解析排除食材列表
    excluded = set()
    if exclude_ingredients:
        for item in exclude_ingredients.replace("，", ",").split(","):
            item = item.strip()
            if item:
                excluded.add(item)

    scored = []
    for r in recipes:
        # 排除用户过敏源
        if user_allergens and r.allergens:
            if set(r.allergens) & user_allergens:
                continue
        # 排除指定食材（检查 materials 字段中的所有值）
        if excluded and r.materials:
            material_values = set()
            for m in r.materials:
                if isinstance(m, dict):
                    for v in m.values():
                        if isinstance(v, str):
                            material_values.add(v.strip())
            if material_values & excluded:
                continue
        rt = _get_taste(r.taste)
        sim = _cosine_similarity(target, rt)
        scored.append({
            "id": r.id,
            "name": r.name,
            "cuisine": r.cuisine,
            "difficulty": r.difficulty,
            "method": r.method,
            "url": f"/recipes/{r.id}",
            "similarity": round(sim, 4),
        })

    scored.sort(key=lambda x: (-x["similarity"], x["id"]))

    return {
        "target_taste": {d: round(target[d], 4) for d in TASTE_DIMS},
        "recommendations": scored[:limit],
        "total": min(len(scored), limit),
    }


def _execute_recipe_info(name: str, db: Session) -> dict:
    """按名称模糊查询食谱（被 AI tool call 调用）

    Args:
        name: 食谱名称，支持模糊匹配
        db: 数据库会话

    Returns:
        食谱详情或匹配列表
    """
    recipes = db.query(Recipe).filter(
        Recipe.is_delete == False,
        Recipe.status == RecipeStatus.PUBLIC,
    ).all()

    if not recipes:
        return {"error": "暂无公开食谱"}

    # 计算名称相似度
    scored = []
    for r in recipes:
        ratio = difflib.SequenceMatcher(None, name, r.name).ratio()
        scored.append((ratio, r))

    # 按相似度降序
    scored.sort(key=lambda x: -x[0])

    best_ratio, best = scored[0]

    # 如果最佳匹配低于阈值，返回候选列表让用户选择
    if best_ratio < 0.2:
        return {"error": f"未找到与「{name}」相关的食谱"}

    r = best
    return {
        "id": r.id,
        "name": r.name,
        "cuisine": r.cuisine,
        "method": r.method,
        "difficulty": r.difficulty,
        "materials": r.materials,
        "seasonings": r.seasonings,
        "steps": r.steps,
        "carbohydrate": r.carbohydrate,
        "protein": r.protein,
        "fat": r.fat,
        "vitamins": r.vitamins,
        "minerals": r.minerals,
        "is_halal": r.is_halal,
        "allergens": r.allergens,
        "url": f"/recipes/{r.id}",
        "match_ratio": round(best_ratio, 4),
    }


def _build_system_prompt() -> str:
    """构建带 skill 说明的系统提示词"""
    return (
        "你是一个智能饮食推荐助手，名叫 EATING AI。你有以下两个工具可用：\n\n"
        "【工具1：recommend_recipes】\n"
        "当用户请求推荐食谱时调用。支持额外参数：\n"
        "- cuisine：筛选菜系，如「川菜」\n"
        "- exclude_ingredients：排除食材，如「鸡蛋,花生」\n"
        "- taste_adjustments：口味微调，如用户说「不要太甜」传入 {\"sweet\":\"decrease\"}\n\n"
        "【工具2：get_recipe_info】\n"
        "当用户询问某道菜的做法、材料、步骤等信息时调用。支持模糊匹配。\n\n"
        "【严格规则】\n"
        "1. 只使用工具返回的数据，绝不编造食谱名称或链接。\n"
        "2. 推荐食谱时使用 [名称](url) 格式，名称和链接来自工具返回数据。\n"
        "3. 查询食谱时如未精确匹配，会进行模糊搜索，返回最接近的结果。\n"
        "4. 如果用户指定了菜系、排除食材或口味要求，请传给 recommend_recipes 的对应参数。"
    )


@router.post("/")
async def chat(
    request: ChatRequest,
    current_user: Person = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """
    流式对话接口（支持 recommend_recipes 工具调用）

    AI 可以在对话中调用 recommend_recipes 工具来获取个性化食谱推荐。
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

    # 构建完整消息列表：system 提示 + 用户消息
    messages = [{"role": "system", "content": _build_system_prompt()}]
    messages.extend(request.messages)

    # ===== 第一阶段：非流式调用，检查是否需要工具调用 =====
    try:
        first_response = client.chat.completions.create(
            model=settings.DEEPSEEK_MODEL,
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto",
        )
    except Exception as e:
        return StreamingResponse(
            iter([f"data: 抱歉，服务出错: {str(e)}\n\n", "data: [DONE]\n\n"]),
            media_type="text/event-stream",
        )

    choice = first_response.choices[0]

    # 如果模型没有调用工具，直接流式返回内容
    if not choice.finish_reason or choice.finish_reason != "tool_calls" or not choice.message.tool_calls:
        content = choice.message.content or ""

        async def stream_initial() -> AsyncGenerator[str, None]:
            # 有直接回复就输出
            if content:
                yield f"data: {content}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            stream_initial(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # ===== 第二阶段：执行工具调用 =====
    assistant_msg = choice.message
    messages.append({
        "role": "assistant",
        "content": assistant_msg.content or "",
        "tool_calls": [
            {
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.function.name, "arguments": tc.function.arguments},
            }
            for tc in assistant_msg.tool_calls
        ],
    })

    # 执行每个工具调用
    for tc in assistant_msg.tool_calls:
        try:
            args = json.loads(tc.function.arguments)
        except json.JSONDecodeError:
            args = {}

        if tc.function.name == "recommend_recipes":
            result = _execute_recommendation(
                current_user.account, db,
                limit=args.get("limit", 10),
                cuisine=args.get("cuisine"),
                exclude_ingredients=args.get("exclude_ingredients"),
                taste_adjustments=args.get("taste_adjustments"),
            )
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result, ensure_ascii=False),
            })
        elif tc.function.name == "get_recipe_info":
            name = args.get("name", "")
            result = _execute_recipe_info(name, db)
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result, ensure_ascii=False),
            })

    # ===== 第三阶段：流式返回最终回复 =====
    async def generate_final() -> AsyncGenerator[str, None]:
        try:
            stream = client.chat.completions.create(
                model=settings.DEEPSEEK_MODEL,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stream=True,
            )
            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield f"data: {chunk.choices[0].delta.content}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            yield f"data: 抱歉，服务出错: {str(e)}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate_final(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
