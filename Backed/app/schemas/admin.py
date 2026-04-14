from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class AdminBase(BaseModel):
    account: str = Field(..., description="管理员账户")
    level: int = Field(..., ge=0, le=9, description="管理员级别(0-9)")


class AdminUpdate(BaseModel):
    level: Optional[int] = Field(None, ge=0, le=9, description="管理员级别(0-9)")
    permission_until: Optional[datetime] = Field(None, description="权限有效期")


class AdminResponse(AdminBase):
    id: int = Field(..., description="管理员ID")
    last_auth_time: Optional[datetime] = Field(None, description="最后认证时间")
    permission_until: Optional[datetime] = Field(None, description="权限有效期")

    model_config = ConfigDict(from_attributes=True)


class AdminResetPasswordRequest(BaseModel):
    """管理员重置密码（需要0级管理员权限）"""
    target_account: str = Field(..., description="目标管理员账户")
    new_password: str = Field(..., description="新密码")


class AdminCreateLevel1(BaseModel):
    """0级管理员创建1级管理员"""
    password: str = Field(..., description="登录密码")
    permission_duration_days: int = Field(30, ge=1, description="权限持续天数(默认30天)")
