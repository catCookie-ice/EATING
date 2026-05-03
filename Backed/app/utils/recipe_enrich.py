"""
食谱智能补充工具

根据食谱的用料自动计算维生素、矿物质、过敏源。
如果遇到数据库中不存在的食材，调用 AI 查询并自动补充入库。
"""

import json
import re
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session

from app.models.ingredient import Ingredient
from app.models.recipe import Recipe
from app.utils.deepseek import simple_chat


# 常见不可量化描述词
_UNMEASURABLE = {"适量", "少许", "若干", "少量", "大量", "极少量", "微量"}


def _parse_weight_to_grams(weight_str: Optional[str]) -> Optional[float]:
    """解析重量字符串为克数

    支持格式：
    - "200g" / "200克" → 200
    - "500ml" / "500毫升" → 500
    - "3个" → 无法精确估算，返回 None
    - "1勺" / "1汤匙" → 15
    - "1茶匙" → 5
    - "适量" / "少许" → None（无法量化）

    Args:
        weight_str: 重量字符串

    Returns:
        克数，无法解析返回 None
    """
    if not weight_str or not isinstance(weight_str, str):
        return None

    text = weight_str.strip()
    if not text:
        return None

    # 不可量化描述
    if text in _UNMEASURABLE:
        return None

    # 提取数字
    match = re.search(r'(\d+\.?\d*)', text)
    if not match:
        return None

    value = float(match.group(1))
    if value <= 0:
        return None

    # 数字后面的部分 = 单位
    unit = text[match.end():].strip()

    # 直接以克/g/ml/毫升为单位的
    if not unit or unit in ("g", "克", "ml", "毫升"):
        return value

    # 勺/匙类
    if "茶匙" in unit or "小匙" in unit:
        return value * 5
    if "汤匙" in unit or "大匙" in unit or "勺" in unit:
        return value * 15

    # 杯
    if "杯" in unit:
        return value * 200

    # 根/条 → 估算为 100g（如黄瓜、胡萝卜等）
    if unit in ("根", "条", "只"):
        return value * 100

    # 其他未知单位 → 无法精确估算
    return None


def _lookup_ingredient(material_name: str, db: Session) -> Optional[Ingredient]:
    """在食材库中查找匹配的食材

    遍历食材名称列表，支持精确和部分匹配

    Args:
        material_name: 食材名称（如"鸡蛋"）
        db: 数据库会话

    Returns:
        匹配的食材对象，未找到返回 None
    """
    ingredients = db.query(Ingredient).filter(Ingredient.is_delete == False).all()
    for ing in ingredients:
        names = ing.name or []
        if isinstance(names, str):
            names = [names]
        for name in names:
            if name == material_name or material_name in name or name in material_name:
                return ing
    return None


def _ai_fetch_ingredient(material_name: str) -> Optional[dict]:
    """调用 AI 查询食材的营养信息

    Args:
        material_name: 食材名称

    Returns:
        食材信息字典，失败返回 None
    """
    prompt = (
        f"请提供食材「{material_name}」的营养成分信息。"
        f"请严格按以下 JSON 格式返回（不要加 markdown 标记，只返回纯 JSON）：\n"
        f'{{\n'
        f'  "name": ["{material_name}"],\n'
        f'  "carbohydrate": 每500克碳水克数(浮点数),\n'
        f'  "protein": 每500克蛋白质克数(浮点数),\n'
        f'  "fat": 每500克脂肪克数(浮点数),\n'
        f'  "vitamins": ["维生素A", "维生素C"...],\n'
        f'  "minerals": ["钙", "铁"...],\n'
        f'  "category": "食材类别(肉/蛋/蔬菜/水果/奶制品/谷物/豆类/坚果/海鲜/其他)",\n'
        f'  "is_allergen": 是否是常见过敏源(true/false),\n'
        f'  "is_halal": 是否清真(true/false)\n'
        f'}}\n\n'
        f"注意：carbohydrate、protein、fat 必须是数字，不要带单位。"
        f"如果不确定具体数值，请给出合理估算值。"
    )

    try:
        result = simple_chat(
            prompt,
            system_prompt="你是一个专业的食品营养数据库，请根据食材的真实营养数据返回 JSON。",
            temperature=0.1,
            max_tokens=1024,
        )
        # 清理可能的 markdown 标记
        text = result.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
            if "```" in text:
                text = text.rsplit("```", 1)[0]
            text = text.strip()

        data = json.loads(text)

        # 验证必要字段
        required = {"name", "carbohydrate", "protein", "fat", "category"}
        if not required.issubset(data.keys()):
            return None

        return {
            "name": data.get("name", [material_name]),
            "carbohydrate": float(data.get("carbohydrate", 0)),
            "protein": float(data.get("protein", 0)),
            "fat": float(data.get("fat", 0)),
            "vitamins": data.get("vitamins", []),
            "minerals": data.get("minerals", []),
            "category": data.get("category", "其他"),
            "is_allergen": bool(data.get("is_allergen", False)),
            "is_halal": bool(data.get("is_halal", False)),
        }
    except Exception:
        return None


def _ensure_ingredient(material_name: str, db: Session, allow_ai: bool = True) -> Optional[Ingredient]:
    """确保食材存在于数据库中，不存在则用AI补充

    Args:
        material_name: 食材名称
        db: 数据库会话
        allow_ai: 是否允许用 AI 自动创建新食材（仅管理员可用）

    Returns:
        食材对象
    """
    # 先查找现有食材
    existing = _lookup_ingredient(material_name, db)
    if existing:
        return existing

    # 不允许 AI 创建则直接返回
    if not allow_ai:
        return None

    # 不存在则调用 AI 查询
    ai_data = _ai_fetch_ingredient(material_name)
    if not ai_data:
        return None

    # 创建新食材
    new_ing = Ingredient(
        name=ai_data["name"],
        carbohydrate=ai_data["carbohydrate"],
        protein=ai_data["protein"],
        fat=ai_data["fat"],
        vitamins=ai_data["vitamins"],
        minerals=ai_data["minerals"],
        category=ai_data["category"],
        is_allergen=ai_data["is_allergen"],
        is_halal=ai_data["is_halal"],
        is_ai=True,
    )
    db.add(new_ing)
    db.commit()
    db.refresh(new_ing)
    return new_ing


def enrich_recipe_from_materials(
    materials: List[Dict[str, Any]],
    db: Session,
    existing_allergens: Optional[List[str]] = None,
    allow_ai: bool = True,
) -> dict:
    """根据食谱用料自动计算营养成分

    遍历食谱的用料列表，在食材库中查找对应的食材，
    根据每种食材的实际重量等比例折算碳水/蛋白/脂肪，
    汇总所有食材的维生素、矿物质列表，并计算过敏源。
    最终营养值按 500g 食谱折算。

    Args:
        materials: 食谱用料列表 [{"材料名": "鸡蛋", "重量": "3个"}, ...]
        db: 数据库会话
        existing_allergens: 用户已经手动填写的过敏源（保留）
        allow_ai: 是否允许AI自动创建不存在的食材（仅管理员可用）

    Returns:
        {"carbohydrate": ..., "protein": ..., "fat": ...,
         "vitamins": [...], "minerals": [...], "allergens": [...]}
    """

    vitamins_set: set = set()
    minerals_set: set = set()
    allergens_set: set = set()
    total_carb = 0.0
    total_protein = 0.0
    total_fat = 0.0
    total_weight = 0.0

    # 保留用户已填写的过敏源
    if existing_allergens:
        for a in existing_allergens:
            allergens_set.add(a)

    for material in materials:
        if not isinstance(material, dict):
            continue

        # 支持多种格式:
        #   {材料名: xxx, 重量: xxx}  — 显式中文 key
        #   {name: xxx, amount: xxx}   — 显式英文 key
        #   {xxx: yyy}                 — key 直接为食材名, value 为用量
        material_name = material.get("材料名") or material.get("name")
        weight_str = material.get("重量") or material.get("amount")

        # 兼容 {食材名: 用量} 格式
        if not material_name:
            for k in material:
                if k not in ("重量", "amount", "材料名", "name"):
                    material_name = k
                    break
        if not material_name or not isinstance(material_name, str):
            continue

        # 兼容 {食材名: 用量} 格式下，如果还没取到用量则从 value 取
        if weight_str is None and material_name in material:
            val = material[material_name]
            if isinstance(val, str):
                weight_str = val

        ingredient = _ensure_ingredient(material_name.strip(), db, allow_ai=allow_ai)
        if not ingredient:
            continue

        # ---- 定量计算：碳水/蛋白/脂肪 ----
        weight_grams = _parse_weight_to_grams(weight_str)
        if weight_grams is not None and weight_grams > 0:
            ratio = weight_grams / 500.0  # 食材库以 500g 为单位
            total_carb += (ingredient.carbohydrate or 0) * ratio
            total_protein += (ingredient.protein or 0) * ratio
            total_fat += (ingredient.fat or 0) * ratio
            total_weight += weight_grams

        # ---- 定性收集：维生素/矿物质/过敏源 ----
        if ingredient.vitamins:
            for v in ingredient.vitamins:
                if isinstance(v, str):
                    vitamins_set.add(v)

        if ingredient.minerals:
            for m in ingredient.minerals:
                if isinstance(m, str):
                    minerals_set.add(m)

        if ingredient.is_allergen:
            allergens_set.add(material_name.strip())

    # 按 500g 食谱折算
    if total_weight > 0:
        scale = 500.0 / total_weight
        carb_per_500g = total_carb * scale
        protein_per_500g = total_protein * scale
        fat_per_500g = total_fat * scale
    else:
        carb_per_500g = 0.0
        protein_per_500g = 0.0
        fat_per_500g = 0.0

    return {
        "carbohydrate": round(carb_per_500g, 2),
        "protein": round(protein_per_500g, 2),
        "fat": round(fat_per_500g, 2),
        "vitamins": sorted(vitamins_set),
        "minerals": sorted(minerals_set),
        "allergens": sorted(allergens_set),
    }
