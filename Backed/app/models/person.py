from sqlalchemy import Column, Integer, String, DateTime, Boolean
from app.database import Base


class Person(Base):
    __tablename__ = "persons"

    id = Column(Integer, primary_key=True, index=True)
    account = Column(String(20), unique=True, nullable=False, index=True, comment="账户")
    password_hash = Column(String(255), nullable=False, comment="BCrypt加密密码")
    status = Column(String(20), default="正常", comment="正常/删除/冻结")
    created_at = Column(DateTime, comment="创建时间")
    must_reset_password = Column(Boolean, default=False, comment="下次登录是否必须重置密码")
    failed_admin_attempts = Column(Integer, default=0, comment="非管理员调用管理员接口失败次数")