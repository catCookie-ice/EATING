"""食谱路由"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
import copy

from app.database import get_db
from app.models.recipe import Recipe
from app.models.admin import Admin
from app.models.person import Person
from app.models.user import User
from app.models.ingredient import Ingredient
from app.schemas.recipe import RecipeCreate, RecipeUpdate, RecipeResponse
from app.dependencies import get_current_admin, get_current_user, require_admin
from app.utils.text_filter import TextFilter
from app.utils.jwt import decode_access_token

router = APIRouter(prefix="/recipes", tags=["食谱"])


# 新建一个独立的路由，专门用于搜索
router_search = APIRouter(prefix="/recipes-search", tags=["食谱搜索"])



def filter_recipe_fields(recipe_data: dict) -> dict:
    """过滤食谱中的文本字段违禁词

    Args:
        recipe_data: 食谱数据字典

    Returns:
        过滤后的食谱数据字典
    """
    recipe_data = copy.deepcopy(recipe_data)

    # 过滤菜名
    if recipe_data.get("name"):
        recipe_data["name"] = TextFilter.filter_text(recipe_data["name"])

    # 过滤材料名
    if recipe_data.get("materials"):
        for item in recipe_data["materials"]:
            if "材料名" in item:
                item["材料名"] = TextFilter.filter_text(item["材料名"])

    # 过滤调料名
    if recipe_data.get("seasonings"):
        for item in recipe_data["seasonings"]:
            if "调料名" in item:
                item["调料名"] = TextFilter.filter_text(item["调料名"])

    # 过滤步骤操作
    if recipe_data.get("steps"):
        for item in recipe_data["steps"]:
            if "操作" in item:
                item["操作"] = TextFilter.filter_text(item["操作"])

    # 过滤菜系
    if recipe_data.get("cuisine"):
        recipe_data["cuisine"] = TextFilter.filter_text(recipe_data["cuisine"])

    return recipe_data


def enrich_recipe_with_source_avatar(recipe: Recipe, db: Session) -> dict:
    """为食谱 enriched 返回数据，包含来源头像和封面图

    Args:
        recipe: 食谱模型实例
        db: 数据库会话

    Returns:
        包含来源头像和封面图的食谱字典
    """
    from app.utils.storage import get_storage

    recipe_dict = {
        "id": recipe.id,
        "name": recipe.name,
        "materials": recipe.materials,
        "seasonings": recipe.seasonings,
        "cuisine": recipe.cuisine,
        "difficulty": recipe.difficulty,
        "steps": recipe.steps,
        "carbohydrate": recipe.carbohydrate,
        "protein": recipe.protein,
        "fat": recipe.fat,
        "vitamins": recipe.vitamins,
        "minerals": recipe.minerals,
        "is_halal": recipe.is_halal,
        "allergens": recipe.allergens,
        "method": recipe.method,
        "pictures_url": recipe.pictures_url,
        "is_delete": recipe.is_delete,
        "source": recipe.source,
        "status": recipe.status,
        "creator_account": recipe.creator_account,
    }

    # 解析封面图URL（混合存储模式下尝试找到真实存在的URL）
    if recipe.pictures_url and isinstance(recipe.pictures_url, list) and len(recipe.pictures_url) > 0:
        storage = get_storage()
        resolved_pictures = []
        for url in recipe.pictures_url:
            resolved_url = storage.find_file(url) or url
            resolved_pictures.append(resolved_url)
        recipe_dict["pictures_url"] = resolved_pictures
    elif recipe.pictures_url:
        recipe_dict["pictures_url"] = recipe.pictures_url
    else:
        recipe_dict["pictures_url"] = []

    # 获取来源头像
    source_avatar_url = None
    # 如果来源不是系统/官方，则尝试获取用户头像
    if recipe.source and recipe.source not in ["系统", "官方"]:
        if recipe.creator_account:
            user = db.query(User).filter(User.account == recipe.creator_account).first()
            if user and user.avatar_url:
                source_avatar_url = user.avatar_url
                # 混合存储模式下，尝试解析真实存在的URL
                storage = get_storage()
                source_avatar_url = storage.find_file(source_avatar_url) or source_avatar_url

    recipe_dict["source_avatar_url"] = source_avatar_url

    return recipe_dict


@router.get("/", response_model=List[RecipeResponse])
def list_recipes(
    skip: int = 0,
    limit: int = 100,
    cuisine: str = None,
    is_halal: bool = None,
    db: Session = Depends(get_db)
):
    """获取公开的食谱列表"""
    from app.schemas.recipe import RecipeStatus

    query = db.query(Recipe).filter(
        Recipe.is_delete == False,
        Recipe.status == RecipeStatus.PUBLIC  # 只显示公开的
    )

    if cuisine:
        query = query.filter(Recipe.cuisine == cuisine)
    if is_halal is not None:
        query = query.filter(Recipe.is_halal == is_halal)

    recipes = query.offset(skip).limit(limit).all()

    # 为每个食谱添加来源头像
    result = []
    for recipe in recipes:
        recipe_dict = enrich_recipe_with_source_avatar(recipe, db)
        result.append(recipe_dict)

    return result


@router.get("/all", response_model=List[RecipeResponse])
def list_all_recipes(
    skip: int = 0,
    limit: int = 100,
    cuisine: str = None,
    is_halal: bool = None,
    status: str = None,
    db: Session = Depends(get_db),
    # admin: Admin = Depends(require_admin)
):
    """获取所有食谱列表 (管理员)"""
    from app.schemas.recipe import RecipeStatus

    query = db.query(Recipe).filter(Recipe.is_delete == False)

    if cuisine:
        query = query.filter(Recipe.cuisine == cuisine)
    if is_halal is not None:
        query = query.filter(Recipe.is_halal == is_halal)
    if status:
        query = query.filter(Recipe.status == status)

    recipes = query.offset(skip).limit(limit).all()

    # 为每个食谱添加来源头像
    result = []
    for recipe in recipes:
        recipe_dict = enrich_recipe_with_source_avatar(recipe, db)
        result.append(recipe_dict)

    return result


@router.get("/my", response_model=List[RecipeResponse])
def list_my_recipes(
    skip: int = 0,
    limit: int = 100,
    person: Person = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取当前用户的食谱列表 (包括私密的)"""
    recipes = db.query(Recipe).filter(
        Recipe.is_delete == False,
        Recipe.creator_account == person.account
    ).offset(skip).limit(limit).all()

    # 为每个食谱添加来源头像
    result = []
    for recipe in recipes:
        recipe_dict = enrich_recipe_with_source_avatar(recipe, db)
        result.append(recipe_dict)

    return result


@router.get("/pending", response_model=List[RecipeResponse])
def list_pending_recipes(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_admin)
):
    """获取待审核的食谱列表 (管理员)"""
    from app.schemas.recipe import RecipeStatus

    recipes = db.query(Recipe).filter(
        Recipe.is_delete == False,
        Recipe.status == RecipeStatus.PENDING,
        Recipe.creator_account.isnot(None)  # 用户分享的
    ).offset(skip).limit(limit).all()

    # 为每个食谱添加来源头像
    result = []
    for recipe in recipes:
        recipe_dict = enrich_recipe_with_source_avatar(recipe, db)
        result.append(recipe_dict)

    return result


@router.get("/{recipe_id}", response_model=RecipeResponse)
def get_recipe(recipe_id: int, db: Session = Depends(get_db)):
    """获取单个食谱"""
    recipe = db.query(Recipe).filter(
        Recipe.id == recipe_id,
        Recipe.is_delete == False
    ).first()

    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="食谱不存在"
        )

    # 添加来源头像
    return enrich_recipe_with_source_avatar(recipe, db)


# 注册新的搜索路由
router.include_router(router_search)


# 新路由中的端点 - 需要放在include_router之后
@router_search.get("/by-ingredient", response_model=List[dict])
def get_recipes_by_ingredient(
    ingredient_id: int,
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """通过食材ID搜索食谱列表"""
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

    # 获取食材的所有名称变体
    ingredient_names = ingredient.name or []
    if isinstance(ingredient_names, list):
        search_names = ingredient_names
    else:
        search_names = [ingredient_names]

    # 查询所有公开食谱
    all_recipes = db.query(Recipe).filter(
        Recipe.is_delete == False,
        Recipe.status == "public"
    ).all()

    # 筛选并计算匹配度
    matched_recipes = []
    recipe_ids = set()

    for recipe in all_recipes:
        materials = recipe.materials or []
        best_match = 0

        for material in materials:
            if not material:
                continue
            material_name = list(material.keys())[0]

            for search_name in search_names:
                # 精确匹配=2分，部分匹配=1分
                if material_name == search_name:
                    best_match = max(best_match, 2)
                elif search_name in material_name or material_name in search_name:
                    best_match = max(best_match, 1)

        if best_match > 0 and recipe.id not in recipe_ids:
            recipe_ids.add(recipe.id)
            matched_recipes.append({
                "id": recipe.id,
                "name": recipe.name,
                "difficulty": recipe.difficulty,
                "cuisine": recipe.cuisine,
                "method": recipe.method,
                "match_score": best_match
            })

    # 排序：匹配度降序，同分按ID
    matched_recipes.sort(key=lambda x: (-x["match_score"], x["id"]))

    # 移除match_score
    for r in matched_recipes:
        r.pop("match_score", None)

    return matched_recipes[skip:skip + limit]


@router.post("/", response_model=RecipeResponse)
def create_recipe(
    recipe: RecipeCreate,
    db: Session = Depends(get_db),
    person: Person = Depends(get_current_user)
):
    """创建食谱 (管理员或用户创建)"""
    from app.schemas.recipe import RecipeStatus

    # 检查是否是管理员
    admin = db.query(Admin).filter(Admin.account == person.account).first()
    is_admin = admin is not None and (not admin.permission_until or admin.permission_until >= datetime.now())

    # 过滤违禁词
    filtered_data = filter_recipe_fields(recipe.model_dump())

    if is_admin:
        # 管理员创建的是系统食谱
        db_recipe = Recipe(**filtered_data)
        db_recipe.source = "系统"
        db_recipe.status = RecipeStatus.PUBLIC
        db_recipe.creator_account = None
    else:
        # 普通用户创建的是个人食谱，需要满足注册15天条件
        user = db.query(User).filter(User.account == person.account).first()
        if user and user.created_at:
            days_since_registration = (datetime.now() - user.created_at).days
            if days_since_registration < 15:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"注册不满15天，暂不能创建食谱。还需等待 {15 - days_since_registration} 天"
                )

        db_recipe = Recipe(**filtered_data)
        db_recipe.status = RecipeStatus.PRIVATE  # 默认私密
        db_recipe.creator_account = person.account
        db_recipe.source = "用户"

    db.add(db_recipe)
    db.commit()
    db.refresh(db_recipe)
    return db_recipe


@router.post("/my", response_model=RecipeResponse)
def create_my_recipe(
    recipe: RecipeCreate,
    person: Person = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建自己的食谱 (用户，不需要等待15天)"""
    from app.schemas.recipe import RecipeStatus

    user = db.query(User).filter(User.account == person.account).first()

    # 创建用户自己的食谱（过滤违禁词）
    filtered_data = filter_recipe_fields(recipe.model_dump())
    if user:
        filtered_data["source"] = TextFilter.filter_text(user.nickname)  # 过滤用户昵称
    else:
        filtered_data["source"] = "用户"
    db_recipe = Recipe(**filtered_data)
    db_recipe.status = RecipeStatus.PRIVATE  # 默认私密
    db_recipe.creator_account = person.account
    db.add(db_recipe)
    db.commit()
    db.refresh(db_recipe)
    return db_recipe


@router.post("/share", response_model=RecipeResponse)
def share_recipe(
    recipe: RecipeCreate,
    person: Person = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """分享食谱 (用户，需要注册超过15天)"""
    # 检查用户注册时间
    user = db.query(User).filter(User.account == person.account).first()
    if not user or not user.created_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户信息不存在"
        )

    # 检查是否超过15天
    days_since_registration = (datetime.now() - user.created_at).days
    if days_since_registration < 15:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"注册不满15天，暂不能分享菜谱。还需等待 {15 - days_since_registration} 天"
        )

    # 创建用户分享的食谱（过滤违禁词）
    from app.schemas.recipe import RecipeStatus

    filtered_data = filter_recipe_fields(recipe.model_dump())
    filtered_data["source"] = TextFilter.filter_text(user.nickname)  # 过滤用户昵称
    db_recipe = Recipe(**filtered_data)
    db_recipe.status = RecipeStatus.PENDING  # 默认待审核
    db_recipe.creator_account = person.account
    db.add(db_recipe)
    db.commit()
    db.refresh(db_recipe)
    return db_recipe


@router.put("/my/{recipe_id}", response_model=RecipeResponse)
def update_my_recipe(
    recipe_id: int,
    recipe_update: RecipeUpdate,
    person: Person = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新用户自己的食谱"""
    db_recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()

    if not db_recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="食谱不存在"
        )

    # 检查是否是自己的食谱
    if db_recipe.creator_account != person.account:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只能操作自己的食谱"
        )

    # 检查是否是系统食谱（管理员创建的），系统食谱用户无法修改
    if not db_recipe.creator_account:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="系统食谱无法修改"
        )

    update_data = recipe_update.model_dump(exclude_unset=True)
    # 用户不能修改 source 和 creator_account
    update_data.pop('source', None)
    update_data.pop('creator_account', None)
    update_data.pop('status', None)  # 用户不能修改状态

    # 过滤违禁词
    update_data = filter_recipe_fields(update_data)

    for key, value in update_data.items():
        setattr(db_recipe, key, value)

    db.commit()
    db.refresh(db_recipe)
    return db_recipe


@router.put("/my/{recipe_id}/share", response_model=RecipeResponse)
def share_my_recipe(
    recipe_id: int,
    person: Person = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """分享用户自己的食谱 (需要注册超过15天，提交审核)"""
    from app.schemas.recipe import RecipeStatus

    # 检查用户注册时间
    user = db.query(User).filter(User.account == person.account).first()
    if not user or not user.created_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户信息不存在"
        )

    # 检查是否超过15天
    days_since_registration = (datetime.now() - user.created_at).days
    if days_since_registration < 15:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"注册不满15天，暂不能分享菜谱。还需等待 {15 - days_since_registration} 天"
        )

    # 检查食谱是否存在
    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="食谱不存在"
        )

    # 检查是否是自己的食谱
    if recipe.creator_account != person.account:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只能操作自己的食谱"
        )

    # 检查是否是系统食谱
    if not recipe.creator_account:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="系统食谱无法分享"
        )

    # 已经是待审核状态
    if recipe.status == RecipeStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="食谱已在审核中"
        )

    # 已经是公开状态
    if recipe.status == RecipeStatus.PUBLIC:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="食谱已经是公开状态"
        )

    # 修改为待审核状态
    recipe.status = RecipeStatus.PENDING
    db.commit()
    db.refresh(recipe)
    return recipe


@router.put("/{recipe_id}/visibility", response_model=RecipeResponse)
def set_recipe_visibility(
    recipe_id: int,
    status: str,
    person: Person = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """设置食谱状态 (用户只能操作自己的食谱，只有公开状态可以设为私密)"""
    from app.schemas.recipe import RecipeStatus

    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()

    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="食谱不存在"
        )

    # 检查是否是自己的食谱
    if recipe.creator_account != person.account:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只能操作自己的食谱"
        )

    # 检查是否是系统食谱（管理员创建的）
    if not recipe.creator_account:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="系统食谱无法修改状态"
        )

    # 只有公开状态的食谱可以设为私密
    if status == "private" and recipe.status != RecipeStatus.PUBLIC:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="只有公开的食谱可以设为私密"
        )

    # 设为公开时，如果是待审核状态则不允许
    if status == "public" and recipe.status == RecipeStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="待审核的食谱无法直接公开"
        )

    # 验证status值
    if status not in ["private", "public"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的状态值"
        )

    recipe.status = RecipeStatus.PRIVATE if status == "private" else RecipeStatus.PUBLIC

    db.commit()
    db.refresh(recipe)
    return recipe


@router.post("/{recipe_id}/approve", response_model=RecipeResponse)
def approve_recipe(
    recipe_id: int,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_admin)
):
    """审核通过食谱 (管理员)"""
    from app.schemas.recipe import RecipeStatus

    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()

    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="食谱不存在"
        )

    # 检查是否是用户分享的食谱
    if not recipe.creator_account:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="系统食谱无需审核"
        )

    recipe.status = RecipeStatus.PUBLIC
    db.commit()
    db.refresh(recipe)
    return recipe


@router.post("/{recipe_id}/reject", response_model=RecipeResponse)
def reject_recipe(
    recipe_id: int,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_admin)
):
    """审核拒绝食谱 (管理员)"""
    from app.schemas.recipe import RecipeStatus

    recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()

    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="食谱不存在"
        )

    # 检查是否是用户分享的食谱
    if not recipe.creator_account:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="系统食谱无需审核"
        )

    recipe.status = RecipeStatus.PRIVATE
    db.commit()
    db.refresh(recipe)
    return recipe


@router.put("/{recipe_id}", response_model=RecipeResponse)
def update_recipe(
    recipe_id: int,
    recipe_update: RecipeUpdate,
    db: Session = Depends(get_db),
    person: Person = Depends(get_current_user)
):
    """更新食谱 (管理员或食谱所有者)"""
    db_recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()

    if not db_recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="食谱不存在"
        )

    # 检查是否是管理员
    admin = db.query(Admin).filter(Admin.account == person.account).first()
    is_admin = admin is not None and (not admin.permission_until or admin.permission_until >= datetime.now())

    # 检查权限：管理员可以更新任何食谱，用户只能更新自己创建的食谱
    if not is_admin:
        if not db_recipe.creator_account:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员可以修改系统食谱"
            )
        if db_recipe.creator_account != person.account:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只能修改自己的食谱"
            )

    update_data = recipe_update.model_dump(exclude_unset=True)
    # 不能修改 source 和 creator_account
    update_data.pop('source', None)
    update_data.pop('creator_account', None)
    # 用户不能修改状态
    if not is_admin:
        update_data.pop('status', None)

    # 过滤违禁词
    update_data = filter_recipe_fields(update_data)

    for key, value in update_data.items():
        setattr(db_recipe, key, value)

    db.commit()
    db.refresh(db_recipe)
    return db_recipe


@router.delete("/{recipe_id}")
def delete_recipe(
    recipe_id: int,
    db: Session = Depends(get_db),
    person: Person = Depends(get_current_user)
):
    """删除食谱 (软删除, 管理员或食谱所有者)"""
    db_recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()

    if not db_recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="食谱不存在"
        )

    # 检查是否是管理员
    admin = db.query(Admin).filter(Admin.account == person.account).first()
    is_admin = admin is not None and (not admin.permission_until or admin.permission_until >= datetime.now())

    # 检查权限：管理员可以删除任何食谱，用户只能删除自己创建的食谱
    if not is_admin:
        if not db_recipe.creator_account:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只有管理员可以删除系统食谱"
            )
        if db_recipe.creator_account != person.account:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="只能删除自己的食谱"
            )

    db_recipe.is_delete = True
    db.commit()

    return {"message": "食谱已删除"}


@router.delete("/my/{recipe_id}")
def delete_my_recipe(
    recipe_id: int,
    person: Person = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除用户自己的食谱 (软删除)"""
    db_recipe = db.query(Recipe).filter(Recipe.id == recipe_id).first()

    if not db_recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="食谱不存在"
        )

    # 检查是否是自己的食谱
    if db_recipe.creator_account != person.account:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只能删除自己的食谱"
        )

    # 检查是否是系统食谱（管理员创建的）
    if not db_recipe.creator_account:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="系统食谱无法删除"
        )

    db_recipe.is_delete = True
    db.commit()

    return {"message": "食谱已删除"}