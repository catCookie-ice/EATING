from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime


class PersonBase(BaseModel):
    account: str = Field(..., description="账户账号")
    status: str = Field("正常", description="账户状态：正常/删除/冻结")


class PersonCreate(BaseModel):
    account: str = Field(..., description="账户账号")
    password: str = Field(..., description="登录密码")


class PersonUpdate(BaseModel):
    status: Optional[str] = Field(None, description="账户状态：正常/删除/冻结")


class PersonResponse(PersonBase):
    id: int = Field(..., description="人员ID")
    created_at: Optional[datetime] = Field(None, description="创建时间")
    must_reset_password: bool = Field(False, description="下次登录是否必须重置密码")

    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    account: str = Field(..., description="账户账号")
    password: str = Field(..., description="登录密码")


class ResetPasswordRequest(BaseModel):
    old_password: str = Field(..., description="旧密码")
    new_password: str = Field(..., description="新密码")


class UserResetPasswordRequest(BaseModel):
    """用户重置密码（不需要登录）"""
    account: str = Field(..., description="账户账号")
    contact: str = Field(..., description="联系方式（手机号或邮箱）")
    new_password: str = Field(..., description="新密码")
