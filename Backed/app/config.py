from pydantic_settings import BaseSettings
from typing import Optional, List


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "mysql+pymysql://root:password@localhost:3306/eating"

    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Admin default
    ADMIN_0_ACCOUNT: str = "a7s90001"
    ADMIN_0_PASSWORD: str = "admin0000"

    # 食材类别枚举
    INGREDIENT_CATEGORIES: List[str] = ["肉", "蛋", "蔬菜", "水果","奶制品","谷物",'豆类', '坚果',"海鲜","其他"]

    # 菜系列表
    CUISINES: List[str] = [
        "川菜", "粤菜", "湘菜", "鲁菜", "苏菜", "浙菜", "闽菜", "徽菜",
        "东北菜", "西北菜","家常菜","西餐", "日料", "韩餐", "东南亚菜", "家常菜","其他"
    ]

    # 烹饪方式列表
    METHODS: List[str] = ["蒸", "煮", "炸", "炒", "焖", "拌", "卤", "烤", "煎", "腌","炖", "其他"]

    class Config:
        env_file = ".env"


settings = Settings()