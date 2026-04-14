from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, Text
from app.database import Base


class Ingredient(Base):
    __tablename__ = "ingredients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(JSON, nullable=False, comment="食材名称列表")
    carbohydrate = Column(Float, nullable=False, comment="碳水(每500g)")
    protein = Column(Float, nullable=False, comment="蛋白质")
    fat = Column(Float, nullable=False, comment="脂肪")
    vitamins = Column(JSON, comment="维生素列表")
    minerals = Column(JSON, comment="矿物质列表")
    category = Column(String(50), nullable=False, comment="种类")
    is_halal = Column(Boolean, default=False, comment="是否清真")
    is_allergen = Column(Boolean, default=False, comment="是否易过敏")
    is_delete = Column(Boolean, default=False, comment="软删除")
    picture_url = Column(String(500), nullable=True, comment="展示图片地址")