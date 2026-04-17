"""用户路由"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models.user import User
from app.models.person import Person
from app.models.admin import Admin
from app.models.recipe import Recipe
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserResponseFull, TastePreference
from app.dependencies import get_current_user, get_current_admin, require_admin
from app.utils.crypto import encrypt_contact, decrypt_contact
from app.utils.text_filter import TextFilter
from app.utils.storage import get_storage
from app.routers.auth import validate_taste, validate_optional_field, validate_gender

router = APIRouter(prefix="/users", tags=["用户"])


def enrich_user_with_avatar_url(user: User, db: Session) -> dict:
    """为用户 enriched 返回数据，包含解析后的头像URL

    Args:
        user: 用户模型实例
        db: 数据库会话

    Returns:
        包含解析后头像URL的用户字典
    """
    user_dict = {
        "id": user.id,
        "account": user.account,
        "nickname": user.nickname,
        "gender": user.gender,
        "age": user.age,
        "taste": user.taste,
        "is_halal": user.is_halal,
        "allergens": user.allergens,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "browse_history": user.browse_history,
        "favorite_records": user.favorite_records,
    }

    # 解析头像URL（混合存储模式下尝试找到真实存在的URL）
    if user.avatar_url:
        storage = get_storage()
        resolved_url = storage.find_file(user.avatar_url)
        user_dict["avatar_url"] = resolved_url or user.avatar_url
    else:
        user_dict["avatar_url"] = None

    return user_dict


@router.get("/me", response_model=UserResponseFull)
def get_current_user_info(
    person: Person = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取当前用户信息"""
    user = db.query(User).filter(User.account == person.account).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户信息不存在"
        )
    # 添加解析后的头像URL
    return enrich_user_with_avatar_url(user, db)


@router.get("/{account}", response_model=UserResponse)
def get_user(
    account: str,
    db: Session = Depends(get_db)
):
    """获取用户信息 (公开信息)"""
    user = db.query(User).filter(User.account == account).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    # 添加解析后的头像URL
    return enrich_user_with_avatar_url(user, db)


@router.put("/me", response_model=UserResponseFull)
def update_current_user(
    user_update: UserUpdate,
    person: Person = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新当前用户信息"""
    user = db.query(User).filter(User.account == person.account).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户信息不存在"
        )

    update_data = user_update.model_dump(exclude_unset=True, exclude={"contact"})
    warnings = []

    # 过滤昵称中的违禁词
    if "nickname" in update_data:
        update_data["nickname"] = TextFilter.filter_text(update_data["nickname"])

    # 处理口味偏好转换为字典和验证
    if "taste" in update_data and update_data["taste"]:
        processed_taste, taste_warning = validate_taste(update_data["taste"])
        if taste_warning:
            warnings.append(taste_warning)
        update_data["taste"] = processed_taste.model_dump()
    elif "taste" in update_data and update_data["taste"] is None:
        # 用户明确设置为null，使用默认值
        default_taste = TastePreference(sour=0.2, sweet=0.2, bitter=0.2, spicy=0.2, salty=0.2)
        update_data["taste"] = default_taste.model_dump()
        warnings.append("口味偏好为空，已使用默认值")

    # 处理可选字段的验证
    if "gender" in update_data:
        processed_value, warning = validate_gender(update_data["gender"])
        if warning:
            warnings.append(warning)
        update_data["gender"] = processed_value
    else:
        # 如果用户没有设置性别，使用默认值
        update_data["gender"] = "私密"

    if "avatar_url" in update_data:
        processed_value, warning = validate_optional_field(update_data["avatar_url"], "头像URL")
        if warning:
            warnings.append(warning)
        update_data["avatar_url"] = processed_value

    # 处理联系方式加密
    if user_update.contact:
        contact_encrypted, contact_key = encrypt_contact(user_update.contact)
        update_data["contact_encrypted"] = contact_encrypted
        update_data["contact_key"] = contact_key

    for key, value in update_data.items():
        setattr(user, key, value)

    db.commit()
    db.refresh(user)

    # 如果有提示信息，附加到响应中
    if warnings:
        from fastapi.responses import JSONResponse
        response_data = {
            "id": user.id,
            "account": user.account,
            "nickname": user.nickname,
            "gender": user.gender,
            "age": user.age,
            "avatar_url": user.avatar_url,
            "taste": user.taste,
            "is_halal": user.is_halal,
            "allergens": user.allergens,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "warnings": warnings
        }
        return JSONResponse(content=response_data)

    return user


@router.put("/{account}", response_model=UserResponseFull)
def update_user(
    account: str,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_admin)
):
    """更新用户信息 (管理员)"""
    user = db.query(User).filter(User.account == account).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    update_data = user_update.model_dump(exclude_unset=True, exclude={"contact"})
    warnings = []

    # 过滤昵称中的违禁词
    if "nickname" in update_data:
        update_data["nickname"] = TextFilter.filter_text(update_data["nickname"])

    # 处理口味偏好转换为字典和验证
    if "taste" in update_data and update_data["taste"]:
        processed_taste, taste_warning = validate_taste(update_data["taste"])
        if taste_warning:
            warnings.append(taste_warning)
        update_data["taste"] = processed_taste.model_dump()
    elif "taste" in update_data and update_data["taste"] is None:
        default_taste = TastePreference(sour=0.2, sweet=0.2, bitter=0.2, spicy=0.2, salty=0.2)
        update_data["taste"] = default_taste.model_dump()
        warnings.append("口味偏好为空，已使用默认值")

    # 处理可选字段的验证
    if "gender" in update_data:
        processed_value, warning = validate_optional_field(update_data["gender"], "性别")
        if warning:
            warnings.append(warning)
        update_data["gender"] = processed_value

    if "avatar_url" in update_data:
        processed_value, warning = validate_optional_field(update_data["avatar_url"], "头像URL")
        if warning:
            warnings.append(warning)
        update_data["avatar_url"] = processed_value

    if user_update.contact:
        contact_encrypted, contact_key = encrypt_contact(user_update.contact)
        update_data["contact_encrypted"] = contact_encrypted
        update_data["contact_key"] = contact_key

    for key, value in update_data.items():
        setattr(user, key, value)

    db.commit()
    db.refresh(user)

    # 如果有提示信息，附加到响应中
    if warnings:
        from fastapi.responses import JSONResponse
        response_data = {
            "id": user.id,
            "account": user.account,
            "nickname": user.nickname,
            "gender": user.gender,
            "age": user.age,
            "avatar_url": user.avatar_url,
            "taste": user.taste,
            "is_halal": user.is_halal,
            "allergens": user.allergens,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "warnings": warnings
        }
        return JSONResponse(content=response_data)

    return user


@router.delete("/{account}")
def delete_user(
    account: str,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_admin)
):
    """删除用户 (软删除，管理员)"""
    person = db.query(Person).filter(Person.account == account).first()
    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    person.status = "删除"
    db.commit()

    return {"message": "用户已删除"}


@router.post("/{account}/freeze")
def freeze_user(
    account: str,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_admin)
):
    """冻结用户 (管理员)"""
    person = db.query(Person).filter(Person.account == account).first()
    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    person.status = "冻结"
    db.commit()

    return {"message": "用户已冻结"}


@router.post("/{account}/unfreeze")
def unfreeze_user(
    account: str,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_admin)
):
    """解冻用户 (管理员)"""
    person = db.query(Person).filter(Person.account == account).first()
    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    person.status = "正常"
    db.commit()

    return {"message": "用户已解冻"}


@router.post("/me/favorites/{recipe_id}")
def add_favorite_recipe(
    recipe_id: int,
    person: Person = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """添加收藏食谱"""
    # 检查食谱是否存在
    recipe = db.query(Recipe).filter(
        Recipe.id == recipe_id,
        Recipe.is_delete == False
    ).first()
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="食谱不存在"
        )

    user = db.query(User).filter(User.account == person.account).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户信息不存在"
        )

    # 获取现有收藏记录（使用list()创建副本，避免修改原始引用）
    favorites = list(user.favorite_records) if user.favorite_records else []

    # 检查是否已经收藏过
    for fav in favorites:
        if fav.get("recipe_id") == recipe_id:
            return {"message": "已收藏过该食谱", "is_favorited": True}

    # 添加新收藏，最多30条
    new_favorite = {"recipe_id": recipe_id, "收藏时间": datetime.now().isoformat()}
    favorites.insert(0, new_favorite)

    # 保持最多30条记录
    if len(favorites) > 30:
        favorites = favorites[:30]

    # 使用 flush + commit 确保变更写入
    user.favorite_records = favorites
    db.flush()
    db.commit()
    db.refresh(user)

    return {"message": "收藏成功", "is_favorited": True}


@router.delete("/me/favorites/{recipe_id}")
def remove_favorite_recipe(
    recipe_id: int,
    person: Person = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """取消收藏食谱"""
    user = db.query(User).filter(User.account == person.account).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户信息不存在"
        )

    favorites = list(user.favorite_records) if user.favorite_records else []

    # 移除收藏记录
    new_favorites = [fav for fav in favorites if fav.get("recipe_id") != recipe_id]
    user.favorite_records = new_favorites
    db.flush()
    db.commit()
    db.refresh(user)

    return {"message": "取消收藏成功", "is_favorited": False}


@router.get("/me/favorites", response_model=List[dict])
def get_user_favorites(
    person: Person = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取用户收藏的食谱列表"""
    user = db.query(User).filter(User.account == person.account).first()
    if not user:
        return []

    from app.utils.storage import get_storage

    favorites = user.favorite_records or []
    result = []
    storage = get_storage()

    for fav in favorites:
        recipe_id = fav.get("recipe_id")
        recipe = db.query(Recipe).filter(
            Recipe.id == recipe_id,
            Recipe.is_delete == False
        ).first()
        if recipe:
            # 解析封面图URL
            pictures_url = []
            if recipe.pictures_url and isinstance(recipe.pictures_url, list) and len(recipe.pictures_url) > 0:
                for url in recipe.pictures_url:
                    resolved_url = storage.find_file(url) or url
                    pictures_url.append(resolved_url)

            # 获取来源头像
            source_avatar_url = None
            if recipe.source and recipe.source not in ["系统", "官方"]:
                if recipe.creator_account:
                    source_user = db.query(User).filter(User.account == recipe.creator_account).first()
                    if source_user and source_user.avatar_url:
                        source_avatar_url = storage.find_file(source_user.avatar_url) or source_user.avatar_url

            result.append({
                "id": recipe.id,
                "name": recipe.name,
                "difficulty": recipe.difficulty,
                "cuisine": recipe.cuisine,
                "method": recipe.method,
                "pictures_url": pictures_url,
                "source": recipe.source,
                "source_avatar_url": source_avatar_url,
                "收藏时间": fav.get("收藏时间")
            })

    return result


@router.post("/me/browse/{recipe_id}")
def record_browse_history(
    recipe_id: int,
    person: Person = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """记录浏览历史"""
    # 检查食谱是否存在
    recipe = db.query(Recipe).filter(
        Recipe.id == recipe_id,
        Recipe.is_delete == False
    ).first()
    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="食谱不存在"
        )

    user = db.query(User).filter(User.account == person.account).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户信息不存在"
        )

    # 获取现有浏览记录
    history = list(user.browse_history) if user.browse_history else []

    # 移除同一食谱的旧浏览记录
    new_history = [h for h in history if h.get("recipe_id") != recipe_id]

    # 添加新浏览记录，最多50条
    new_history.insert(0, {"recipe_id": recipe_id, "浏览时间": datetime.now().isoformat()})

    # 保持最多50条记录
    if len(new_history) > 50:
        new_history = new_history[:50]

    user.browse_history = new_history
    db.flush()
    db.commit()
    db.refresh(user)

    return {"message": "浏览记录已保存"}