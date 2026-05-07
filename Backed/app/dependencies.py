"""依赖注入"""
import time
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.models.person import Person
from app.models.admin import Admin
from app.utils.jwt import decode_access_token
from app.utils.redis_cache import blacklist_token, is_token_blacklisted
from datetime import datetime

security = HTTPBearer()

# 冻结阈值
MAX_FAILED_ADMIN_ATTEMPTS = 3


'''
用于检查是否登录
'''
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """获取并验证token，返回用户信息"""
    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效凭证或登录已过期",
            # 添加 WWW-Authenticate 头是 HTTP 401 规范推荐的做法
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 可选：检查 token 类型是否为 access_token（如果你在生成 token 时加了这个字段）
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的Token类型",
        )

    # 检查token是否被拉黑
    if is_token_blacklisted(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token已失效，请重新登录",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Person:
    """获取当前登录用户"""
    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭据",
        )

    # 检查token是否被拉黑
    if is_token_blacklisted(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token已失效，请重新登录",
        )

    account = payload.get("sub")
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭据",
        )

    person = db.query(Person).filter(Person.account == account).first()
    if person is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )

    if person.status == "删除":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户已被删除",
        )

    return person


def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Admin:
    """获取当前登录管理员"""
    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭据",
        )

    # 检查token是否被拉黑
    if is_token_blacklisted(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token已失效，请重新登录",
        )

    account = payload.get("sub")
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭据",
        )

    admin = db.query(Admin).filter(Admin.account == account).first()
    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="管理员不存在",
        )

    # 检查权限是否过期
    if admin.permission_until and admin.permission_until < datetime.now():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="管理员权限已过期",
        )

    return admin


def require_level_0_admin(admin: Admin = Depends(get_current_admin)) -> Admin:
    """要求0级管理员"""
    if admin.level != 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要0级管理员权限",
        )
    return admin


def require_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Admin:
    """要求管理员权限，非管理员调用时记录失败次数并可能冻结账户"""
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

    person = db.query(Person).filter(Person.account == account).first()
    if person is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )

    # 检查token是否被拉黑
    if is_token_blacklisted(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token已失效，请重新登录",
        )

    # 检查是否为管理员
    admin = db.query(Admin).filter(Admin.account == account).first()
    if admin is None:
        # 非管理员，记录失败次数
        if person.failed_admin_attempts is None:
            person.failed_admin_attempts = 1
        else:
            person.failed_admin_attempts += 1

        if person.failed_admin_attempts >= MAX_FAILED_ADMIN_ATTEMPTS:
            person.status = "冻结"
            db.commit()

            # 将当前token加入黑名单，使其立即失效
            exp = payload.get("exp")
            if exp:
                remaining = int(exp - time.time())
                if remaining > 0:
                    blacklist_token(token, remaining)

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您没有该权限，且账户已被冻结",
            )

        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您没有该权限",
        )

    # 检查权限是否过期
    if admin.permission_until and admin.permission_until < datetime.now():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="管理员权限已过期",
        )

    return admin


def get_optional_current_user(request: Request) -> Optional[dict]:
    """可选用户认证 - 不会因未登录而报错，仅返回用户信息或None

    - 未登录/无token → 返回 None
    - token有效 → 返回 token payload（含 account）
    - token无效/过期 → 返回 None（不抛异常）
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None

    try:
        scheme, token = auth_header.split(None, 1)
        if scheme.lower() != "bearer":
            return None
    except ValueError:
        return None

    payload = decode_access_token(token)
    if payload is None:
        return None
    return payload