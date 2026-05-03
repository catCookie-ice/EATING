from pydantic import BaseModel, Field, ConfigDict, field_validator
from typing import Optional, List
from app.config import settings


class IngredientBase(BaseModel):
    name: List[str] = Field(..., description="食材名称列表")
    carbohydrate: float = Field(..., description="碳水含量(每500g)")
    protein: float = Field(..., description="蛋白质含量")
    fat: float = Field(..., description="脂肪含量")
    vitamins: Optional[List[str]] = Field(None, description="维生素列表")
    minerals: Optional[List[str]] = Field(None, description="矿物质列表")
    category: str = Field(..., description="食材种类")
    is_halal: bool = Field(False, description="是否清真")
    is_allergen: bool = Field(False, description="是否易过敏")
    is_ai: bool = Field(False, description="是否由AI自动添加")
    picture_url: Optional[str] = Field(None, description="展示图片地址")

    @field_validator('category', mode='before')
    @classmethod
    def validate_category(cls, v):
        if v not in settings.INGREDIENT_CATEGORIES:
            return "其他"
        return v


class IngredientCreate(IngredientBase):
    pass


class IngredientUpdate(BaseModel):
    name: Optional[List[str]] = Field(None, description="食材名称列表")
    carbohydrate: Optional[float] = Field(None, description="碳水含量(每500g)")
    protein: Optional[float] = Field(None, description="蛋白质含量")
    fat: Optional[float] = Field(None, description="脂肪含量")
    vitamins: Optional[List[str]] = Field(None, description="维生素列表")
    minerals: Optional[List[str]] = Field(None, description="矿物质列表")
    category: Optional[str] = Field(None, description="食材种类")
    is_halal: Optional[bool] = Field(None, description="是否清真")
    is_allergen: Optional[bool] = Field(None, description="是否易过敏")
    picture_url: Optional[str] = Field(None, description="展示图片地址")

    @field_validator('category', mode='before')
    @classmethod
    def validate_category(cls, v):
        if v is None:
            return v
        if v not in settings.INGREDIENT_CATEGORIES:
            return "其他"
        return v


class IngredientResponse(IngredientBase):
    id: int = Field(..., description="食材ID")
    is_delete: bool = Field(..., description="是否已删除")
    picture_url: Optional[str] = Field(None, description="展示图片地址")

    model_config = ConfigDict(from_attributes=True)


class PaginatedIngredientResponse(BaseModel):
    """分页食材列表响应"""
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页数量")
    items: List[IngredientResponse] = Field(..., description="食材列表")
