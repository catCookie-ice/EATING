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


class ForgotPasswordGetEmailResponse(BaseModel):
    """获取加密邮箱信息响应"""
    email_key: str = Field(..., description="邮箱验证密钥(前四位)")
    masked_email: str = Field(..., description="脱敏邮箱，如 abcd****@gmail.com")


class ConfirmEmailRequest(BaseModel):
    """确认邮箱请求"""
    account: str = Field(..., description="账户账号")


class SendCodeRequest(BaseModel):
    """发送验证码请求"""
    account: str = Field(..., description="账户账号")


class VerifyCodeRequest(BaseModel):
    """验证验证码请求"""
    account: str = Field(..., description="账户账号")
    code: str = Field(..., description="验证码")


class ForgotPasswordResetRequest(BaseModel):
    """忘记密码-重置密码请求"""
    account: str = Field(..., description="账户账号")
    new_password: str = Field(..., description="新密码")
    reset_token: str = Field(..., description="重置令牌")


class SendChangeEmailCodeRequest(BaseModel):
    """发送换绑邮箱验证码请求"""
    pass


class VerifyChangeEmailCodeRequest(BaseModel):
    """验证换绑邮箱验证码请求"""
    code: str = Field(..., description="验证码")


class VerifyChangeEmailPasswordRequest(BaseModel):
    """密码验证换绑邮箱请求"""
    password: str = Field(..., description="当前密码")


class UpdateEmailRequest(BaseModel):
    """更新邮箱请求"""
    new_contact: str = Field(..., description="新联系方式（邮箱或手机号）")
    verified_token: str = Field(..., description="验证令牌")
