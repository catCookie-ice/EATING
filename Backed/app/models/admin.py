from sqlalchemy import Column, Integer, String, DateTime
from app.database import Base


class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True)
    account = Column(String(20), unique=True, nullable=False, index=True, comment="管理员账户")
    level = Column(Integer, nullable=False, comment="0或1级")
    last_auth_time = Column(DateTime, comment="上次授权时间")
    permission_until = Column(DateTime, comment="权限截止时间")