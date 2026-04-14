"""管理员路由"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
import random
import string

from app.database import get_db
from app.models.admin import Admin
from app.models.person import Person
from app.models.user import User
from app.schemas.admin import AdminUpdate, AdminResponse, AdminResetPasswordRequest, AdminCreateLevel1
from app.schemas.user import UserResponseForAdmin
from app.dependencies import get_current_admin, require_level_0_admin, require_admin
from app.utils.password import hash_password

router = APIRouter(prefix="/admins", tags=["管理员"])


def generate_admin_account(db: Session) -> str:
    """生成管理员账户: 4位随机字符 + 4位递增"""
    # 获取最后一个管理员账户
    last_admin = db.query(Admin).order_by(Admin.account.desc()).first()

    if last_admin:
        # 提取后4位数字
        try:
            suffix = int(last_admin.account[-4:])
            new_suffix = suffix + 1
            suffix_str = str(new_suffix).zfill(4)
        except:
            suffix_str = "0001"
    else:
        suffix_str = "0001"

    # 生成4位随机前缀
    prefix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
    return f"{prefix}{suffix_str}"


@router.get("/", response_model=List[AdminResponse])
def list_admins(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_level_0_admin)
):
    """获取管理员列表 (仅0级管理员可执行，只返回1级管理员)"""
    admins = db.query(Admin).filter(Admin.level != 0).offset(skip).limit(limit).all()
    return admins


@router.get("/me", response_model=AdminResponse)
def get_current_admin_info(admin: Admin = Depends(require_admin)):
    """获取当前管理员信息"""
    return admin


@router.get("/users", response_model=List[UserResponseForAdmin])
def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_admin)
):
    """获取用户列表 (仅1级管理员可执行，0级管理员不能获取用户列表)"""
    # 0级管理员不能获取用户列表
    if admin.level == 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="0级管理员不能获取用户列表"
        )

    users = db.query(User).offset(skip).limit(limit).all()
    return users


@router.get("/{account}", response_model=AdminResponse)
def get_admin(
    account: str,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_admin)
):
    """获取管理员信息"""
    admin_obj = db.query(Admin).filter(Admin.account == account).first()
    if not admin_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="管理员不存在"
        )
    return admin_obj


@router.post("/ctadmin", response_model=AdminResponse)
def create_level1_admin(
    admin_data: AdminCreateLevel1,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_level_0_admin)
):
    """创建1级管理员 (仅0级管理员可执行，1级管理员不加入用户表)"""
    # 生成管理员账户
    account = generate_admin_account(db)

    # 加密密码
    password_hash = hash_password(admin_data.password)

    # 计算权限截止时间
    permission_until = datetime.now() + timedelta(days=admin_data.permission_duration_days)

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

    # 创建管理员记录（1级管理员不加入用户表）
    admin_record = Admin(
        account=account,
        level=1,
        last_auth_time=datetime.now(),
        permission_until=permission_until
    )
    db.add(admin_record)
    db.commit()
    db.refresh(admin_record)

    return admin_record


@router.put("/{account}", response_model=AdminResponse)
def update_admin(
    account: str,
    admin_update: AdminUpdate,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_level_0_admin)
):
    """更新管理员信息 (仅0级管理员可执行)"""
    db_admin = db.query(Admin).filter(Admin.account == account).first()

    if not db_admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="管理员不存在"
        )

    update_data = admin_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_admin, key, value)

    db.commit()
    db.refresh(db_admin)
    return db_admin


@router.delete("/{account}")
def delete_admin(
    account: str,
    db: Session = Depends(get_db),
    admin: Admin = Depends(require_level_0_admin)
):
    """删除管理员 (仅0级管理员可执行)"""
    db_admin = db.query(Admin).filter(Admin.account == account).first()

    if not db_admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="管理员不存在"
        )

    # 不能删除0级管理员
    if db_admin.level == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除0级管理员"
        )

    # 删除管理员记录
    db.delete(db_admin)

    # 删除人员记录
    person = db.query(Person).filter(Person.account == account).first()
    if person:
        person.status = "删除"

    db.commit()

    return {"message": "管理员已删除"}


@router.post("/reset-password")
def admin_reset_password(
    password_data: AdminResetPasswordRequest,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(require_level_0_admin)
):
    """重置管理员密码 (仅0级管理员可执行)"""
    # 查找目标管理员
    target_admin = db.query(Admin).filter(Admin.account == password_data.target_account).first()
    if not target_admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="目标管理员不存在"
        )

    # 查找目标人员
    target_person = db.query(Person).filter(Person.account == password_data.target_account).first()
    if not target_person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="目标人员不存在"
        )

    # 更新密码
    target_person.password_hash = hash_password(password_data.new_password)
    db.commit()

    return {"message": f"管理员 {password_data.target_account} 的密码已重置"}