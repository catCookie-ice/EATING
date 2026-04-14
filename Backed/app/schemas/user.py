from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Literal, Dict, Any
from datetime import datetime


# 性别类型字面量
GenderType = Literal["男", "女", "私密"]


class TastePreference(BaseModel):
    """口味偏好"""
    sour: float = Field(0, ge=0, le=1, description="酸味占比(0-1)")
    sweet: float = Field(0, ge=0, le=1, description="甜味占比(0-1)")
    bitter: float = Field(0, ge=0, le=1, description="苦味占比(0-1)")
    spicy: float = Field(0, ge=0, le=1, description="辣味占比(0-1)")
    salty: float = Field(0, ge=0, le=1, description="咸味占比(0-1)")


class UserBase(BaseModel):
    account: str = Field(..., description="账户账号")
    nickname: str = Field(..., description="用户昵称")
    gender: Optional[GenderType] = Field("私密", description="性别：男/女/私密")
    age: Optional[int] = Field(None, description="年龄")
    avatar_url: Optional[str] = Field(None, description="头像URL地址")
    taste: Optional[TastePreference] = Field(None, description="口味偏好：酸甜苦辣咸占比")
    is_halal: bool = Field(False, description="是否清真人员")
    allergens: Optional[List[str]] = Field(None, description="过敏源列表")


class UserCreate(BaseModel):
    """用户注册 - 只接收昵称、密码、联系方式三个参数"""
    nickname: str = Field(..., description="用户昵称")
    password: str = Field(..., description="登录密码")
    contact: Optional[str] = Field(None, description="联系方式：邮箱或手机号（找回用）")


class UserUpdate(BaseModel):
    nickname: Optional[str] = Field(None, description="用户昵称")
    contact: Optional[str] = Field(None, description="联系方式：邮箱或手机号")
    gender: Optional[GenderType] = Field(None, description="性别：男/女/私密")
    age: Optional[int] = Field(None, description="年龄")
    avatar_url: Optional[str] = Field(None, description="头像URL地址")
    taste: Optional[TastePreference] = Field(None, description="口味偏好：酸甜苦辣咸占比")
    is_halal: Optional[bool] = Field(None, description="是否清真人员")
    allergens: Optional[List[str]] = Field(None, description="过敏源列表")


class UserResponse(UserBase):
    id: int = Field(..., description="用户ID")
    contact_encrypted: Optional[str] = Field(None, description="加密的联系方式")
    contact_key: Optional[str] = Field(None, description="加密密钥(4位)")

    model_config = ConfigDict(from_attributes=True)


class UserResponseForAdmin(BaseModel):
    """管理员获取用户列表时的返回格式"""
    account: str = Field(..., description="账户账号")
    nickname: str = Field(..., description="用户昵称")
    gender: Optional[GenderType] = Field("私密", description="性别")
    avatar_url: Optional[str] = Field(None, description="头像URL地址")
    is_halal: bool = Field(False, description="是否清真人员")

    model_config = ConfigDict(from_attributes=True)


class UserResponseFull(UserBase):
    id: int = Field(..., description="用户ID")
    created_at: Optional[datetime] = Field(None, description="用户创建时间")
    browse_history: Optional[List[Dict[str, Any]]] = Field(None, description="浏览记录 [{食谱ID, 浏览时间}], 最多50条")
    favorite_records: Optional[List[Dict[str, Any]]] = Field(None, description="收藏记录 [{食谱ID, 收藏时间}], 最多30条")

    model_config = ConfigDict(from_attributes=True)