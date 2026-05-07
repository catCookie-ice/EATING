"""认证路由 - 登录注册"""
import random
import json
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
import re

from app.database import get_db
from app.models.person import Person
from app.models.user import User
from app.models.admin import Admin
from app.schemas.person import (
    PersonCreate, LoginRequest, ResetPasswordRequest, UserResetPasswordRequest,
    ForgotPasswordGetEmailResponse, ConfirmEmailRequest, SendCodeRequest,
    VerifyCodeRequest, ForgotPasswordResetRequest,
    SendChangeEmailCodeRequest, VerifyChangeEmailCodeRequest,
    VerifyChangeEmailPasswordRequest, UpdateEmailRequest,
)
from app.schemas.user import UserCreate, UserResponse, TastePreference
from app.schemas.person import PersonResponse
from app.utils.password import hash_password, verify_password
from app.utils.jwt import create_access_token
from app.utils.crypto import encrypt_contact, decrypt_contact
from app.utils.text_filter import TextFilter
from app.utils.redis_cache import get_redis
from app.utils.email_sender import send_email
from app.config import settings
from app.dependencies import get_current_admin, get_current_user, security

router = APIRouter(prefix="/auth", tags=["认证"])

# 禁止传入的字段值
INVALID_VALUES = {"null", "NULL", "undefined", "string", "char", "int", "float", "double", " "}


def validate_field(value: str, field_name: str) -> None:
    """验证字段值是否有效

    Args:
        value: 待验证的值
        field_name: 字段名称（用于错误信息）

    Raises:
        HTTPException: 如果值无效
    """
    if value is not None and value in INVALID_VALUES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name}不能为无效值"
        )


def validate_taste(taste: Optional[TastePreference]) -> tuple[TastePreference, str]:
    """验证口味偏好，如果占比和不为1则使用默认值

    Args:
        taste: 用户输入的口味偏好

    Returns:
        (处理后的口味偏好, 提示信息)
    """
    # 默认口味：每个口味0.2
    default_taste = TastePreference(
        sour=0.2, sweet=0.2, bitter=0.2, spicy=0.2, salty=0.2
    )

    if taste is None:
        return default_taste, "未设置口味偏好，已使用默认值"

    # 计算占比总和
    total = taste.sour + taste.sweet + taste.bitter + taste.spicy + taste.salty

    # 如果和不为1，使用默认值
    if abs(total - 1.0) > 0.001:  # 允许浮点数精度误差
        return default_taste, "口味占比和不为1，已使用默认值"

    return taste, ""


def validate_optional_field(value: Optional[str], field_name: str) -> tuple[Optional[str], str]:
    """验证可选字段，处理无效值

    Args:
        value: 字段值
        field_name: 字段名称

    Returns:
        (处理后的值, 提示信息)
    """
    if value is not None and value in INVALID_VALUES:
        return None, f"{field_name}为无效值，已设置为空"

    # 去除首尾空格后检查空字符串
    if value is not None and value.strip() == "":
        return None, f"{field_name}为空，已设置为空"

    return value, ""


def validate_gender(gender: Optional[str]) -> tuple[Optional[str], str]:
    """验证性别字段

    Args:
        gender: 性别值

    Returns:
        (处理后的性别, 提示信息)
    """
    # 有效值列表
    valid_genders = {"男", "女", "私密"}

    # 如果为 None 或无效值，使用默认值
    if gender is None or gender in INVALID_VALUES:
        return "私密", f"性别为无效值，已设置为默认值私密"

    # 去除空格后检查
    gender_stripped = gender.strip()
    if gender_stripped == "":
        return "私密", "性别为空，已设置为默认值私密"

    # 检查是否在有效值列表中
    if gender_stripped not in valid_genders:
        return "私密", f"性别 {gender} 不在有效值范围内，已设置为默认值私密"

    return gender_stripped, ""


def validate_all_fields(user_data: UserCreate) -> tuple[list[str], Optional[str]]:
    """验证用户创建数据中的所有字段

    Args:
        user_data: 用户创建数据

    Returns:
        (提示信息列表, 加密后的联系方式)
    """
    warnings = []

    # 验证必填字段
    validate_field(user_data.nickname, "昵称")
    validate_field(user_data.password, "密码")

    # 验证并处理可选字段
    contact, contact_warning = validate_optional_field(user_data.contact, "联系方式")
    if contact_warning:
        warnings.append(contact_warning)

    return warnings, contact


def generate_user_account(db: Session) -> str:
    """生成8位递增用户账户"""
    # 获取最后一个用户账户
    last_person = db.query(Person).filter(
        Person.account.like("1%")
    ).order_by(Person.account.desc()).first()

    if last_person:
        try:
            last_num = int(last_person.account)
            new_num = last_num + 1
            return str(new_num).zfill(8)
        except:
            pass

    # 如果没有用户，从10000001开始
    return "10000001"


@router.post("/register", response_model=PersonResponse)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """用户注册 - 只接收昵称、密码、联系方式三个参数"""
    # 验证所有字段，获取处理后的值和提示信息
    warnings, contact = validate_all_fields(user_data)

    # 无论account是否有值，都由程序生成
    account = generate_user_account(db)

    # 检查账户是否已存在（理论上不会发生，因为是新生成的）
    existing = db.query(Person).filter(Person.account == account).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="账户已存在"
        )

    # 检查昵称是否已存在（先过滤违禁词）
    filtered_nickname = TextFilter.filter_text(user_data.nickname)
    existing_nickname = db.query(User).filter(User.nickname == filtered_nickname).first()
    if existing_nickname:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="昵称已存在"
        )

    # 加密密码
    password_hash = hash_password(user_data.password)

    # 创建人员记录
    person = Person(
        account=account,
        password_hash=password_hash,
        status="正常",
        created_at=datetime.now()
    )
    db.add(person)
    db.commit()
    db.refresh(person)

    # 加密联系方式
    contact_encrypted = None
    contact_key = None
    if contact:
        contact_encrypted, contact_key = encrypt_contact(contact)

    # 创建用户记录（默认字段）
    user = User(
        account=account,
        nickname=filtered_nickname,
        contact_encrypted=contact_encrypted,
        contact_key=contact_key,
        gender="私密",
        created_at=datetime.now()
    )
    db.add(user)
    db.commit()

    # 无论是否有警告，都返回成功响应（包含生成的账户）
    response_content = {
        "id": person.id,
        "account": person.account,
        "status": person.status,
        "created_at": person.created_at.isoformat() if person.created_at else None,
    }

    if warnings:
        response_content["warnings"] = warnings

    if warnings:
        return JSONResponse(content=response_content)

    return JSONResponse(content=response_content)


@router.post("/login")
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    """登录"""
    # 查找人员记录
    person = db.query(Person).filter(Person.account == login_data.account).first()

    if not person:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="账户或密码错误"
        )

    # 检查状态
    if person.status == "删除":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="账户已被删除"
        )
    if person.status == "冻结":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账户已被冻结"
        )

    # 验证密码
    if not verify_password(login_data.password, person.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="账户或密码错误"
        )

    # 判断是否为管理员
    admin = db.query(Admin).filter(Admin.account == person.account).first()
    is_admin = admin is not None
    admin_level = admin.level if admin else None

    # 检查是否需要重置密码
    must_reset = person.must_reset_password if person else False

    # 生成Token（将admin信息加入token）
    token_data = {"sub": person.account}
    if is_admin:
        token_data["is_admin"] = True
        token_data["admin_level"] = admin_level
    if must_reset:
        token_data["must_reset_password"] = True

    token = create_access_token(token_data)

    return {
        "access_token": token,
        "is_admin": is_admin,
        "token_type": "bearer",
        "account": person.account
    }


@router.get("/check-admin")
def check_admin_status(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """检查当前用户是否为管理员 (不累加failed_admin_attempts)"""
    from app.utils.jwt import decode_access_token
    from datetime import datetime

    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭据",
        )

    account = payload.get("sub")
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭据",
        )

    # 检查是否为管理员
    admin = db.query(Admin).filter(Admin.account == account).first()
    if admin is None:
        return {"is_admin": False, "admin_level": None}

    # 检查权限是否过期
    if admin.permission_until and admin.permission_until < datetime.now():
        return {"is_admin": False, "admin_level": None, "detail": "管理员权限已过期"}

    return {"is_admin": True, "admin_level": admin.level}


@router.post("/reset-password")
def reset_password(
    password_data: ResetPasswordRequest,
    db: Session = Depends(get_db),
    person: Person = Depends(get_current_user)
):
    """重置密码 (需要已登录)"""
    # 验证旧密码
    if not verify_password(password_data.old_password, person.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="旧密码错误"
        )

    # 检查是否为 0 级管理员，如果是则强制要求重置
    admin = db.query(Admin).filter(Admin.account == person.account).first()
    if admin and admin.level == 0 and person.must_reset_password:
        # 检查新密码是否与初始密码相同
        if password_data.old_password == password_data.new_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="新密码不能与旧密码相同"
            )

    # 更新密码
    person.password_hash = hash_password(password_data.new_password)

    # 如果是 0 级管理员首次重置，取消强制重置标记
    if admin and admin.level == 0:
        person.must_reset_password = False
        # 更新管理员的最后认证时间
        admin.last_auth_time = datetime.now()
        admin.permission_until = datetime.now()

    db.commit()

    return {"message": "密码已更新"}


@router.post("/user-reset-password")
def user_reset_password(
    password_data: UserResetPasswordRequest,
    db: Session = Depends(get_db)
):
    """用户重置密码 (不需要登录，通过联系方式验证)"""
    # 查找账户
    person = db.query(Person).filter(Person.account == password_data.account).first()
    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="账户不存在"
        )

    # 检查是否为管理员
    admin = db.query(Admin).filter(Admin.account == password_data.account).first()
    if admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="管理员账户请联系管理员重置密码"
        )

    # 查找用户信息，验证联系方式
    user = db.query(User).filter(User.account == password_data.account).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户信息不存在"
        )

    # 更新密码
    person.password_hash = hash_password(password_data.new_password)
    db.commit()

    return {"message": "密码已重置，请使用新密码登录"}


# ==================== 找回密码（忘记密码）流程 ====================

@router.get("/forgot-password/{account}")
def forgot_password_get_email(
    account: str,
    db: Session = Depends(get_db)
):
    """根据账户获取加密邮箱，返回邮箱验证密钥（前四位）"""
    # 查找用户
    user = db.query(User).filter(User.account == account).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )

    if not user.contact_encrypted or not user.contact_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该用户未设置联系方式"
        )

    if '@' not in user.contact_encrypted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该用户的联系方式不是邮箱，无法通过邮箱找回密码"
        )

    # 从加密邮箱中提取前四位（加密邮箱格式：前4位明文 + 加密部分@域名）
    local = user.contact_encrypted.split('@')[0]
    if len(local) < 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱格式无效"
        )

    email_key = local[:4]

    # 解密获取完整邮箱（用于生成脱敏显示）
    raw_email = decrypt_contact(user.contact_encrypted, user.contact_key)

    # 生成脱敏邮箱
    if '@' in raw_email:
        raw_local, raw_domain = raw_email.split('@', 1)
        if len(raw_local) > 4:
            masked_email = f"{raw_local[:4]}****@{raw_domain}"
        else:
            masked_email = raw_email
    else:
        masked_email = raw_email

    # 存储到 Redis (1分钟有效)
    r = get_redis()
    info_key = f"pwd_reset:info:{account}"
    info_data = {
        "encrypted": user.contact_encrypted,
        "key": user.contact_key,
        "email_key": email_key
    }
    r.setex(info_key, 60, json.dumps(info_data))

    return ForgotPasswordGetEmailResponse(email_key=email_key, masked_email=masked_email)


@router.post("/forgot-password/confirm-email")
def forgot_password_confirm_email(
    req: ConfirmEmailRequest,
    db: Session = Depends(get_db)
):
    """确认邮箱（用户确认邮箱属于自己后调用）"""
    r = get_redis()
    info_key = f"pwd_reset:info:{req.account}"
    info_data = r.get(info_key)

    if not info_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证信息已过期，请重新获取"
        )

    info = json.loads(info_data)

    # 解密完整邮箱
    raw_email = decrypt_contact(info["encrypted"], info["key"])

    # 存储解密后的邮箱 (10分钟有效)
    email_key = f"pwd_reset:email:{req.account}"
    r.setex(email_key, 600, raw_email)

    # 删除旧的 info
    r.delete(info_key)

    return {"message": "邮箱确认成功"}


@router.post("/forgot-password/send-code")
def forgot_password_send_code(
    req: SendCodeRequest
):
    """发送验证码到已确认的邮箱，1分钟冷却"""
    r = get_redis()

    # 检查冷却期 (1分钟)
    cooldown_key = f"pwd_reset:sent:{req.account}"
    if r.get(cooldown_key):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="发送过于频繁，请等待1分钟后再试"
        )

    # 获取解密后的邮箱
    email_key = f"pwd_reset:email:{req.account}"
    email = r.get(email_key)

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="未确认邮箱或邮箱已过期，请重新验证邮箱"
        )

    # 生成4位随机验证码
    code = ''.join(random.choices('0123456789', k=4))

    # 存储验证码 (1分钟有效)
    code_key = f"pwd_reset:code:{req.account}"
    r.setex(code_key, 60, code)

    # 设置冷却 (1分钟)
    r.setex(cooldown_key, 60, "1")

    # 发送邮件
    subject = "EATING - 密码重置验证码"
    body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #333;">密码重置</h2>
        <p style="font-size: 14px; color: #666;">您正在重置密码，请使用以下验证码：</p>
        <div style="text-align: center; margin: 30px 0;">
            <span style="font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #333; background: #f5f5f5; padding: 15px 30px; border-radius: 8px;">{code}</span>
        </div>
        <p style="font-size: 12px; color: #999;">验证码有效期为10分钟，请尽快完成验证。</p>
        <p style="font-size: 12px; color: #999;">如果这不是您本人的操作，请忽略此邮件。</p>
    </div>
    """

    success = send_email(email, subject, body)
    if not success:
        # 发送失败，清除验证码和冷却
        r.delete(code_key)
        r.delete(cooldown_key)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="邮件发送失败，请稍后重试"
        )

    return {"message": "验证码发送成功，请前往邮箱确认"}


@router.post("/forgot-password/verify-code")
def forgot_password_verify_code(
    req: VerifyCodeRequest
):
    """验证邮箱验证码"""
    r = get_redis()

    code_key = f"pwd_reset:code:{req.account}"
    stored_code = r.get(code_key)

    if not stored_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码已过期，请重新发送"
        )

    if stored_code != req.code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码错误"
        )

    # 生成重置令牌 (2分钟有效)
    reset_token = ''.join(
        random.choices('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz', k=32)
    )
    verified_key = f"pwd_reset:verified:{req.account}"
    r.setex(verified_key, 120, reset_token)

    # 清理验证码和邮箱信息
    r.delete(code_key)
    r.delete(f"pwd_reset:sent:{req.account}")
    r.delete(f"pwd_reset:email:{req.account}")

    return {"message": "验证码正确", "reset_token": reset_token}


@router.post("/forgot-password/reset")
def forgot_password_reset(
    req: ForgotPasswordResetRequest,
    db: Session = Depends(get_db)
):
    """通过忘记密码流程重置密码（需携带重置令牌）"""
    r = get_redis()

    # 验证重置令牌
    verified_key = f"pwd_reset:verified:{req.account}"
    stored_token = r.get(verified_key)

    if not stored_token or stored_token != req.reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="重置令牌无效或已过期"
        )

    # 查找人员
    person = db.query(Person).filter(Person.account == req.account).first()
    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="账户不存在"
        )

    # 检查是否为管理员
    admin = db.query(Admin).filter(Admin.account == req.account).first()
    if admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="管理员账户请联系管理员重置密码"
        )

    # 更新密码
    person.password_hash = hash_password(req.new_password)
    db.commit()

    # 清理所有Redis记录
    r.delete(verified_key)
    r.delete(f"pwd_reset:info:{req.account}")
    r.delete(f"pwd_reset:email:{req.account}")
    r.delete(f"pwd_reset:code:{req.account}")
    r.delete(f"pwd_reset:sent:{req.account}")

    return {"message": "密码已重置，请使用新密码登录"}


# ==================== 换绑邮箱流程 ====================

@router.post("/change-email/send-code")
def change_email_send_code(
    req: SendChangeEmailCodeRequest,
    db: Session = Depends(get_db),
    person: Person = Depends(get_current_user),
):
    """发送换绑邮箱验证码到当前邮箱（需登录）"""
    user = db.query(User).filter(User.account == person.account).first()
    if not user or not user.contact_encrypted or '@' not in user.contact_encrypted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="当前用户未绑定邮箱"
        )

    r = get_redis()

    # 检查冷却期
    cooldown_key = f"change_email:sent:{person.account}"
    if r.get(cooldown_key):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="发送过于频繁，请等待1分钟后再试"
        )

    # 解密当前邮箱
    email = decrypt_contact(user.contact_encrypted, user.contact_key)

    # 生成4位验证码
    code = ''.join(random.choices('0123456789', k=4))

    # 存储验证码 (1分钟)
    code_key = f"change_email:code:{person.account}"
    r.setex(code_key, 60, code)

    # 设置冷却 (1分钟)
    r.setex(cooldown_key, 60, "1")

    # 发送邮件
    subject = "EATING - 换绑邮箱验证码"
    body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #333;">换绑邮箱验证</h2>
        <p style="font-size: 14px; color: #666;">您正在更换绑定邮箱，请使用以下验证码：</p>
        <div style="text-align: center; margin: 30px 0;">
            <span style="font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #333; background: #f5f5f5; padding: 15px 30px; border-radius: 8px;">{code}</span>
        </div>
        <p style="font-size: 12px; color: #999;">验证码有效期为1分钟，请尽快完成验证。</p>
        <p style="font-size: 12px; color: #999;">如果这不是您本人的操作，请忽略此邮件。</p>
    </div>
    """

    success = send_email(email, subject, body)
    if not success:
        r.delete(code_key)
        r.delete(cooldown_key)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="邮件发送失败，请稍后重试"
        )

    return {"message": "验证码已发送至当前邮箱"}


@router.post("/change-email/verify-code")
def change_email_verify_code(
    req: VerifyChangeEmailCodeRequest,
    person: Person = Depends(get_current_user),
):
    """验证换绑邮箱验证码"""
    r = get_redis()
    code_key = f"change_email:code:{person.account}"
    stored_code = r.get(code_key)

    if not stored_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码已过期，请重新发送"
        )

    if stored_code != req.code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码错误"
        )

    # 生成验证令牌 (5分钟有效)
    verified_token = ''.join(
        random.choices('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz', k=32)
    )
    verified_key = f"change_email:verified:{person.account}"
    r.setex(verified_key, 300, verified_token)

    # 清理验证码
    r.delete(code_key)
    r.delete(f"change_email:sent:{person.account}")

    return {"message": "验证通过", "verified_token": verified_token}


@router.post("/change-email/verify-password")
def change_email_verify_password(
    req: VerifyChangeEmailPasswordRequest,
    person: Person = Depends(get_current_user),
):
    """通过密码验证换绑邮箱"""
    if not verify_password(req.password, person.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="密码错误"
        )

    # 生成验证令牌 (5分钟有效)
    verified_token = ''.join(
        random.choices('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz', k=32)
    )
    verified_key = f"change_email:verified:{person.account}"
    r = get_redis()
    r.setex(verified_key, 300, verified_token)

    # 清理可能存在的验证码相关key
    r.delete(f"change_email:code:{person.account}")
    r.delete(f"change_email:sent:{person.account}")

    return {"message": "验证通过", "verified_token": verified_token}


@router.post("/change-email/update")
def change_email_update(
    req: UpdateEmailRequest,
    db: Session = Depends(get_db),
    person: Person = Depends(get_current_user),
):
    """换绑邮箱（需携带验证令牌）"""
    r = get_redis()
    verified_key = f"change_email:verified:{person.account}"
    stored_token = r.get(verified_key)

    if not stored_token or stored_token != req.verified_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证令牌无效或已过期，请重新验证"
        )

    # 加密新联系方式
    new_encrypted, new_key = encrypt_contact(req.new_contact)

    # 更新用户
    user = db.query(User).filter(User.account == person.account).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户信息不存在"
        )

    user.contact_encrypted = new_encrypted
    user.contact_key = new_key
    db.commit()

    # 清理验证令牌
    r.delete(verified_key)

    return {"message": "邮箱已更新"}