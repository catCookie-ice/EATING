from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, Text
from app.database import Base


class Recipe(Base):
    __tablename__ = "recipes"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, comment="菜品名")
    materials = Column(JSON, comment="所需材料 [{材料名, 重量}]")
    seasonings = Column(JSON, comment="所需调料 [{调料名, 用量}]")
    cuisine = Column(String(50), comment="所属菜系")
    difficulty = Column(Float, nullable=False, comment="难度(1-10)")
    steps = Column(JSON, comment="制作步骤 [{时刻, 操作}]")
    carbohydrate = Column(Float, comment="碳水")
    protein = Column(Float, comment="蛋白质")
    fat = Column(Float, comment="脂肪")
    vitamins = Column(JSON, comment="维生素列表")
    minerals = Column(JSON, comment="矿物质列表")
    is_halal = Column(Boolean, default=False, comment="是否清真")
    allergens = Column(JSON, comment="包含的过敏食材列表")
    is_delete = Column(Boolean, default=False, comment="软删除")

    # 新增字段
    source = Column(String(50), default="系统", comment="来源: 系统/用户昵称")
    status = Column(String(20), default="private", comment="状态: private(私密)/public(公开)/pending(申请公开)/appealing(申请解封)/banned(封禁)")
    creator_account = Column(String(20), nullable=True, comment="创建者账户(用户分享时记录)")
    method = Column(String(20), comment="烹饪方式: 蒸/煮/炸/炒/焖/拌/卤/烤/煎/腌/其他")
    taste = Column(JSON, comment="口味占比 {酸, 甜, 苦, 辣, 咸}")
    pictures_url = Column(JSON, nullable=True, comment="展示图片地址列表")