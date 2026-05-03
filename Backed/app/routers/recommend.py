"""
AI 推荐路由

提供基于用户口味偏好、浏览历史和收藏记录的综合食谱推荐
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.dependencies import get_current_user
from app.models.person import Person
from app.models.user import User
from app.models.recipe import Recipe
from app.schemas.recipe import RecipeStatus

router = APIRouter(prefix="/recommend", tags=["AI 推荐"])

# 口味维度名称
TASTE_DIMENSIONS = ["sour", "sweet", "bitter", "spicy", "salty"]

# 权重配置
WEIGHT_PERSONAL = 0.5    # 个人口味占比权重
WEIGHT_FAVORITES = 0.3   # 收藏食谱口味权重
WEIGHT_BROWSE = 0.2      # 浏览记录口味权重

# 默认均等口味
DEFAULT_TASTE = {d: 0.2 for d in TASTE_DIMENSIONS}


def get_taste_vector(taste_dict: Optional[dict]) -> dict:
    """安全获取口味向量，缺失维度用默认值补齐

    Args:
        taste_dict: 口味字典，如 {"sour": 0.2, "sweet": 0.3, ...}

    Returns:
        包含全部五个维度的口味字典
    """
    if not taste_dict or not isinstance(taste_dict, dict):
        return dict(DEFAULT_TASTE)

    result = {}
    for dim in TASTE_DIMENSIONS:
        val = taste_dict.get(dim)
        if val is not None and isinstance(val, (int, float)):
            result[dim] = float(val)
        else:
            result[dim] = 0.2
    return result


def compute_weighted_taste(
    personal_taste: dict,
    favorite_tastes: List[dict],
    browse_tastes: List[dict],
) -> dict:
    """计算加权综合口味占比

    权重: 个人(0.5) > 收藏(0.3) > 浏览(0.2)

    Args:
        personal_taste: 用户个人口味
        favorite_tastes: 收藏食谱的口味列表
        browse_tastes: 浏览食谱的口味列表

    Returns:
        综合口味占比字典
    """
    result = {}

    for dim in TASTE_DIMENSIONS:
        # 个人口味
        personal_val = personal_taste.get(dim, 0.2) * WEIGHT_PERSONAL

        # 收藏食谱平均口味
        if favorite_tastes:
            fav_avg = sum(t.get(dim, 0.2) for t in favorite_tastes) / len(favorite_tastes)
        else:
            fav_avg = 0.2
        favorite_val = fav_avg * WEIGHT_FAVORITES

        # 浏览食谱平均口味
        if browse_tastes:
            browse_avg = sum(t.get(dim, 0.2) for t in browse_tastes) / len(browse_tastes)
        else:
            browse_avg = 0.2
        browse_val = browse_avg * WEIGHT_BROWSE

        result[dim] = round(personal_val + favorite_val + browse_val, 4)

    return result


def compute_taste_similarity(taste_a: dict, taste_b: dict) -> float:
    """计算两个口味的相似度 (基于余弦相似度)

    Args:
        taste_a: 口味A
        taste_b: 口味B

    Returns:
        相似度分数 0-1，越高越相似
    """
    vec_a = [taste_a.get(d, 0) for d in TASTE_DIMENSIONS]
    vec_b = [taste_b.get(d, 0) for d in TASTE_DIMENSIONS]

    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = sum(a * a for a in vec_a) ** 0.5
    norm_b = sum(b * b for b in vec_b) ** 0.5

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot_product / (norm_a * norm_b)


def has_allergen_conflict(recipe_allergens: Optional[list], user_allergens: Optional[list]) -> bool:
    """检查食谱是否含有用户过敏源

    Args:
        recipe_allergens: 食谱的过敏食材列表
        user_allergens: 用户的过敏源列表

    Returns:
        有冲突返回True
    """
    if not user_allergens or not recipe_allergens:
        return False
    return bool(set(recipe_allergens) & set(user_allergens))


@router.get("/")
def get_recommendations(
    limit: int = 10,
    person: Person = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取AI食谱推荐

    基于用户的口味偏好、浏览历史和收藏记录，计算综合口味占比，
    推荐最匹配口味且不含用户过敏源的食谱。

    Args:
        limit: 返回推荐数量，最多20条
    """
    user = db.query(User).filter(User.account == person.account).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户信息不存在"
        )

    limit = min(limit, 20)

    # 1. 获取用户个人口味
    personal_taste = get_taste_vector(user.taste)

    # 2. 获取收藏食谱的口味
    favorite_tastes = []
    favorite_records = user.favorite_records or []
    for fav in favorite_records[:30]:
        recipe_id = fav.get("recipe_id")
        if recipe_id:
            recipe = db.query(Recipe).filter(
                Recipe.id == recipe_id,
                Recipe.is_delete == False
            ).first()
            if recipe and recipe.taste:
                favorite_tastes.append(get_taste_vector(recipe.taste))

    # 3. 获取浏览食谱的口味
    browse_tastes = []
    browse_history = user.browse_history or []
    for entry in browse_history[:50]:
        recipe_id = entry.get("recipe_id")
        if recipe_id:
            recipe = db.query(Recipe).filter(
                Recipe.id == recipe_id,
                Recipe.is_delete == False
            ).first()
            if recipe and recipe.taste:
                browse_tastes.append(get_taste_vector(recipe.taste))

    # 4. 计算综合口味占比
    target_taste = compute_weighted_taste(personal_taste, favorite_tastes, browse_tastes)

    # 5. 获取所有公开食谱
    user_allergens = user.allergens or []

    all_public_recipes = db.query(Recipe).filter(
        Recipe.is_delete == False,
        Recipe.status == RecipeStatus.PUBLIC,
    ).all()

    # 6. 计算相似度并过滤过敏源
    scored_recipes = []
    for recipe in all_public_recipes:
        # 跳过过敏源冲突
        if has_allergen_conflict(recipe.allergens, user_allergens):
            continue

        recipe_taste = get_taste_vector(recipe.taste)
        similarity = compute_taste_similarity(target_taste, recipe_taste)

        scored_recipes.append({
            "id": recipe.id,
            "name": recipe.name,
            "cuisine": recipe.cuisine,
            "difficulty": recipe.difficulty,
            "method": recipe.method,
            "pictures_url": recipe.pictures_url,
            "similarity_score": round(similarity, 4),
            "taste": recipe_taste,
        })

    # 7. 按相似度降序排列，取top N
    scored_recipes.sort(key=lambda x: (-x["similarity_score"], x["id"]))

    result = scored_recipes[:limit]

    return {
        "target_taste": target_taste,
        "recommendations": result,
        "total": len(result),
    }
