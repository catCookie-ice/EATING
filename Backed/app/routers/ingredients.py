"""食材路由"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.config import settings
from app.models.ingredient import Ingredient
from app.models.recipe import Recipe
from app.models.admin import Admin
from app.schemas.ingredient import IngredientCreate, IngredientUpdate, IngredientResponse, PaginatedIngredientResponse
from app.dependencies import require_admin, get_optional_current_user
from app.utils.text_filter import TextFilter
from app.utils.storage import get_storage
from app.utils.redis_cache import make_cache_key, get_cache, set_cache, delete_cache_pattern

router = APIRouter(prefix="/ingredients", tags=["食材"])


def delete_old_file(old_url: str):
    """删除旧文件"""
    if not old_url:
        return
    try:
        storage = get_storage()
        storage.delete(old_url)
    except Exception:
        # 删除失败静默处理，不影响主流程
        pass


def enrich_ingredient_with_picture_url(ingredient: Ingredient, db: Session) -> dict:
    """为食材 enriched 返回数据，包含解析后的封面图片URL

    Args:
        ingredient: 食材模型实例
        db: 数据库会话

    Returns:
        包含解析后封面URL的食材字典
    """
    ingredient_dict = {
        "id": ingredient.id,
        "name": ingredient.name,
        "carbohydrate": ingredient.carbohydrate,
        "protein": ingredient.protein,
        "fat": ingredient.fat,
        "vitamins": ingredient.vitamins,
        "minerals": ingredient.minerals,
        "category": ingredient.category,
        "is_halal": ingredient.is_halal,
        "is_allergen": ingredient.is_allergen,
        "is_ai": ingredient.is_ai,
        "is_delete": ingredient.is_delete,
    }

    # 解析封面图片URL（混合存储模式下尝试找到真实存在的URL）
    if ingredient.picture_url:
        storage = get_storage()
        resolved_url = storage.find_file(ingredient.picture_url)
        ingredient_dict["picture_url"] = resolved_url or ingredient.picture_url
    else:
        ingredient_dict["picture_url"] = None

    return ingredient_dict


@router.get("/", response_model=PaginatedIngredientResponse)
def list_ingredients(
    page: int = 1,
    page_size: int = 20,
    category: str = None,
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_current_user),
):
    """获取食材列表（分页 + Redis 缓存）

    未登录用户只能获取第1页数据
    """
    # 参数校验
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 20
    if page_size > 100:
        page_size = 100

    # 未登录用户只能获取第1页
    if current_user is None and page > 1:
        page = 1

    # 尝试从缓存读取
    cache_key = make_cache_key(
        "ingredients:list",
        page=page,
        page_size=page_size,
        category=category,
    )
    cached = get_cache(cache_key)
    if cached is not None:
        return cached

    # 查询数据库
    query = db.query(Ingredient).filter(Ingredient.is_delete == False)

    if category:
        query = query.filter(Ingredient.category == category)

    total = query.count()
    ingredients = query.order_by(Ingredient.id).offset((page - 1) * page_size).limit(page_size).all()

    # 为每个食材添加解析后的封面URL
    items = []
    for ingredient in ingredients:
        ingredient_dict = enrich_ingredient_with_picture_url(ingredient, db)
        items.append(ingredient_dict)

    result = {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }

    # 写入缓存
    set_cache(cache_key, result, ttl=settings.REDIS_CACHE_TTL_INGREDIENTS)

    return result


@router.get("/{ingredient_id}", response_model=IngredientResponse)
def get_ingredient(ingredient_id: int, db: Session = Depends(get_db)):
    """获取单个食材"""
    ingredient = db.query(Ingredient).filter(
        Ingredient.id == ingredient_id,
        Ingredient.is_delete == False
    ).first()

    if not ingredient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="食材不存在"
        )

    # 添加解析后的封面URL
    return enrich_ingredient_with_picture_url(ingredient, db)


# 这个接口需要重启后端才能生效
# @router.get("/used-by", response_model=List[dict])
# def search_recipes_by_ingredient(...)
    # 先获取食材名称
    ingredient = db.query(Ingredient).filter(
        Ingredient.id == ingredient_id,
        Ingredient.is_delete == False
    ).first()

    if not ingredient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="食材不存在"
        )

    # 获取食材的所有名称变体（可能有多个名称）
    ingredient_names = ingredient.name or []
    if isinstance(ingredient_names, list):
        search_names = ingredient_names
    else:
        search_names = [ingredient_names]

    # 查询所有公开食谱
    from app.models.recipe import Recipe
    from app.schemas.recipe import RecipeStatus

    all_recipes = db.query(Recipe).filter(
        Recipe.is_delete == False,
        Recipe.status == RecipeStatus.PUBLIC
    ).all()

    # 筛选出包含该食材的食谱，计算匹配度
    # 匹配度：精确匹配=2，部分匹配=1
    matched_recipes = []
    recipe_ids = set()  # 防止重复

    for recipe in all_recipes:
        materials = recipe.materials or []
        best_match = 0  # 该食谱的最佳匹配度

        for material in materials:
            if not material:
                continue
            material_name = list(material.keys())[0]

            for search_name in search_names:
                # 精确匹配（完全相等）
                if material_name == search_name:
                    best_match = max(best_match, 2)
                # 部分匹配（包含关系，但不相等）
                elif search_name in material_name or material_name in search_name:
                    best_match = max(best_match, 1)

        if best_match > 0:
            if recipe.id not in recipe_ids:
                recipe_ids.add(recipe.id)
                matched_recipes.append({
                    "id": recipe.id,
                    "name": recipe.name,
                    "difficulty": recipe.difficulty,
                    "cuisine": recipe.cuisine,
                    "method": recipe.method,
                    "match_score": best_match
                })

    # 按匹配度降序排序（精确匹配在前），匹配度相同则按id排序
    matched_recipes.sort(key=lambda x: (-x["match_score"], x["id"]))

    # 移除match_score字段
    for r in matched_recipes:
        r.pop("match_score", None)

    return matched_recipes[skip:skip + limit]


@router.post("/", response_model=IngredientResponse)
def create_ingredient(
    ingredient: IngredientCreate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_admin)
):
    """创建食材 (需要管理员权限)"""
    # 过滤违禁词
    ingredient_data = ingredient.model_dump()
    if ingredient_data.get("name"):
        ingredient_data["name"] = TextFilter.filter_text_list(ingredient_data["name"])
    if ingredient_data.get("category"):
        ingredient_data["category"] = TextFilter.filter_text(ingredient_data["category"])

    db_ingredient = Ingredient(**ingredient_data)
    db.add(db_ingredient)
    db.commit()
    db.refresh(db_ingredient)
    # 创建食材后使列表缓存失效
    delete_cache_pattern("ingredients:list:*")
    return db_ingredient


@router.put("/{ingredient_id}", response_model=IngredientResponse)
def update_ingredient(
    ingredient_id: int,
    ingredient_update: IngredientUpdate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_admin)
):
    """更新食材 (需要管理员权限)"""
    db_ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()

    if not db_ingredient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="食材不存在"
        )

    update_data = ingredient_update.model_dump(exclude_unset=True)

    # 删除旧的封面图片
    if "picture_url" in update_data and update_data["picture_url"]:
        if db_ingredient.picture_url and update_data["picture_url"] != db_ingredient.picture_url:
            delete_old_file(db_ingredient.picture_url)

    # 过滤违禁词
    if update_data.get("name"):
        update_data["name"] = TextFilter.filter_text_list(update_data["name"])
    if update_data.get("category"):
        update_data["category"] = TextFilter.filter_text(update_data["category"])

    for key, value in update_data.items():
        setattr(db_ingredient, key, value)

    db.commit()
    db.refresh(db_ingredient)
    # 更新食材后使列表缓存失效
    delete_cache_pattern("ingredients:list:*")
    return db_ingredient


@router.delete("/{ingredient_id}")
def delete_ingredient(
    ingredient_id: int,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_admin)
):
    """删除食材 (软删除, 需要管理员权限)"""
    db_ingredient = db.query(Ingredient).filter(Ingredient.id == ingredient_id).first()

    if not db_ingredient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="食材不存在"
        )

    db_ingredient.is_delete = True
    db.commit()
    # 删除食材后使列表缓存失效
    delete_cache_pattern("ingredients:list:*")

    return {"message": "食材已删除"}