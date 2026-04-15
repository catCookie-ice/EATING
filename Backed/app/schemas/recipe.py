from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from typing import Optional, List, Dict, Any
from enum import Enum
from app.config import settings


class RecipeStatus(str, Enum):
    """食谱状态枚举"""
    PRIVATE = "private"  # 私密
    PUBLIC = "public"    # 公开
    PENDING = "pending"  # 待审核


class MaterialItem(BaseModel):
    材料名: str = Field(..., description="材料名称")
    重量: str = Field(..., description="材料重量")


class SeasoningItem(BaseModel):
    调料名: str = Field(..., description="调料名称")
    用量: str = Field(..., description="调料用量")


class StepItem(BaseModel):
    """步骤项，键值对由用户自定义"""
    pass


class RecipeBase(BaseModel):
    name: str = Field(..., description="菜品名称")
    materials: List[Dict[str, Any]] = Field(..., description="所需材料列表 [{材料名, 重量}]")
    seasonings: List[Dict[str, Any]] = Field(..., description="所需调料列表 [{调料名, 用量}]")
    cuisine: str = Field(..., description="所属菜系")
    difficulty: float = Field(..., ge=1, le=10, description="难度(1-10)")
    steps: List[Dict[str, Any]] = Field(..., description="制作步骤列表，每个步骤为键值对")
    carbohydrate: Optional[float] = Field(None, gt=0, le=999999, description="碳水含量(>0)")
    protein: Optional[float] = Field(None, gt=0, le=999999, description="蛋白质含量(>0)")
    fat: Optional[float] = Field(None, gt=0, le=999999, description="脂肪含量(>0)")
    vitamins: Optional[List[str]] = Field(None, description="维生素列表")
    minerals: Optional[List[str]] = Field(None, description="矿物质列表")
    is_halal: bool = Field(False, description="是否清真")
    allergens: Optional[List[str]] = Field(None, description="过敏食材列表")
    method: Optional[str] = Field(None, description="烹饪方式: 蒸/煮/炸/炒/焖/拌/卤/烤/煎/腌/其他")
    pictures_url: Optional[List[str]] = Field(None, description="展示图片地址列表，最多3个")

    @field_validator('cuisine', mode='before')
    @classmethod
    def validate_cuisine(cls, v):
        if v not in settings.CUISINES:
            return "其他"
        return v

    @field_validator('method', mode='before')
    @classmethod
    def validate_method(cls, v):
        if v is None:
            return v
        if v not in settings.METHODS:
            return "其他"
        return v

    @field_validator('carbohydrate', 'protein', 'fat', mode='before')
    @classmethod
    def round_to_two_decimals(cls, v):
        if v is None:
            return v
        if isinstance(v, (int, float)):
            # 四舍五入到两位小数
            return round(v, 2)
        return v

    @model_validator(mode='after')
    def validate_pictures_url(self):
        if self.pictures_url and len(self.pictures_url) > 3:
            self.pictures_url = self.pictures_url[:3]
        return self


class RecipeCreate(RecipeBase):
    status: Optional[RecipeStatus] = Field(RecipeStatus.PRIVATE, description="状态: private(私密)/public(公开)/pending(待审核)")


class RecipeUpdate(BaseModel):
    name: Optional[str] = Field(None, description="菜品名称")
    materials: Optional[List[Dict[str, Any]]] = Field(None, description="所需材料列表")
    seasonings: Optional[List[Dict[str, Any]]] = Field(None, description="所需调料列表")
    cuisine: Optional[str] = Field(None, description="所属菜系")
    difficulty: Optional[float] = Field(None, ge=1, le=10, description="难度(1-10)")
    steps: Optional[List[Dict[str, Any]]] = Field(None, description="制作步骤列表")
    carbohydrate: Optional[float] = Field(None, gt=0, le=999999, description="碳水含量(>0)")
    protein: Optional[float] = Field(None, gt=0, le=999999, description="蛋白质含量(>0)")
    fat: Optional[float] = Field(None, gt=0, le=999999, description="脂肪含量(>0)")
    vitamins: Optional[List[str]] = Field(None, description="维生素列表")
    minerals: Optional[List[str]] = Field(None, description="矿物质列表")
    is_halal: Optional[bool] = Field(None, description="是否清真")
    allergens: Optional[List[str]] = Field(None, description="过敏食材列表")
    status: Optional[RecipeStatus] = Field(None, description="状态: private(私密)/public(公开)/pending(待审核)")
    method: Optional[str] = Field(None, description="烹饪方式: 蒸/煮/炸/炒/焖/拌/卤/烤/煎/腌/其他")
    pictures_url: Optional[List[str]] = Field(None, description="展示图片地址列表，最多3个")

    @field_validator('cuisine', mode='before')
    @classmethod
    def validate_cuisine(cls, v):
        if v is None:
            return v
        if v not in settings.CUISINES:
            return "其他"
        return v

    @field_validator('method', mode='before')
    @classmethod
    def validate_method(cls, v):
        if v is None:
            return v
        if v not in settings.METHODS:
            return "其他"
        return v

    @field_validator('carbohydrate', 'protein', 'fat', mode='before')
    @classmethod
    def round_to_two_decimals(cls, v):
        if v is None:
            return v
        if isinstance(v, (int, float)):
            return round(v, 2)
        return v


class RecipeResponse(RecipeBase):
    id: int = Field(..., description="食谱ID")
    is_delete: bool = Field(..., description="是否已删除")
    source: Optional[str] = Field("系统", description="来源：系统/用户昵称")
    status: RecipeStatus = Field(RecipeStatus.PRIVATE, description="状态: private(私密)/public(公开)/pending(待审核)")
    creator_account: Optional[str] = Field(None, description="创建者账户")
    method: Optional[str] = Field(None, description="烹饪方式: 蒸/煮/炸/炒/焖/拌/卤/烤/煎/腌/其他")
    pictures_url: Optional[List[str]] = Field(None, description="展示图片地址列表，最多3个")
    source_avatar_url: Optional[str] = Field(None, description="来源头像URL（如果来源不是系统或官方）")

    model_config = ConfigDict(from_attributes=True)
