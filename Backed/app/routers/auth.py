"""认证路由 - 登录注册"""
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
from app.schemas.person import PersonCreate, LoginRequest, ResetPasswordRequest, UserResetPasswordRequest
from app.schemas.user import UserCreate, UserResponse, TastePreference
from app.schemas.person import PersonResponse
from app.utils.password import hash_password, verify_password
from app.utils.jwt import create_access_token
from app.utils.crypto import encrypt_contact
from app.utils.text_filter import TextFilter
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