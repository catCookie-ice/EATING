from sqlalchemy import Column, Integer, String, Float, Boolean, JSON, DateTime
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    account = Column(String(20), unique=True, nullable=False, index=True, comment="关联账户")
    nickname = Column(String(50), nullable=False, unique=True, comment="昵称")
    contact_encrypted = Column(String(255), comment="加密的邮箱/手机")
    contact_key = Column(String(4), comment="加密密钥(4位)")
    gender = Column(String(10), comment="性别")
    age = Column(Integer, comment="年龄")
    avatar_url = Column(String(500), comment="头像URL")
    taste = Column(JSON, comment="口味占比 {酸, 甜, 苦, 辣, 咸}")
    is_halal = Column(Boolean, default=False, comment="是否清真人员")
    allergens = Column(JSON, comment="过敏源列表")
    created_at = Column(DateTime, comment="用户创建时间")
    browse_history = Column(JSON, comment="浏览记录 [{食谱ID, 浏览时间}], 最多50条")
    favorite_records = Column(JSON, comment="收藏记录 [{食谱ID, 收藏时间}], 最多30条")