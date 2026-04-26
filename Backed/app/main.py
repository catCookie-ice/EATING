"""FastAPI 应用入口"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from datetime import datetime
import os

from app.database import engine, Base, get_db
from app.models.person import Person
from app.models.admin import Admin
from app.routers import auth, ingredients, recipes, users, admins, upload, chat
from app.config import settings
from app.utils.password import hash_password


def datetime_serializer(dt: datetime) -> str:
    """自定义 datetime 序列化"""
    return dt.isoformat()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时创建数据库表
    Base.metadata.create_all(bind=engine)

    # 检查并创建 0 级管理员
    db = next(get_db())
    existing_admin_0 = db.query(Admin).filter(Admin.level == 0).first()
    if not existing_admin_0:
        # 从配置获取 0 级管理员账户和密码
        admin_account = settings.ADMIN_0_ACCOUNT
        admin_password = settings.ADMIN_0_PASSWORD

        # 检查人员记录是否已存在
        existing_person = db.query(Person).filter(Person.account == admin_account).first()
        if not existing_person:
            # 创建人员记录
            person = Person(
                account=admin_account,
                password_hash=hash_password(admin_password),
                status="正常",
                created_at=datetime.now(),
                must_reset_password=True  # 首次登录必须重置密码
            )
            db.add(person)
            db.commit()
            db.refresh(person)

        # 确保 0 级管理员记录存在（如果不存在则创建，如果存在但被删则恢复）
        admin_0 = db.query(Admin).filter(Admin.account == admin_account).first()
        if not admin_0:
            admin_0 = Admin(
                account=admin_account,
                level=0,
                last_auth_time=datetime.now(),
                permission_until=datetime.now()
            )
            db.add(admin_0)
            db.commit()
        elif admin_0.level != 0:
            # 如果存在但是非0级，修改为0级
            admin_0.level = 0
            db.commit()

        print(f"已创建/恢复内置 0 级管理员账户: {admin_account}")

    yield
    # 关闭时清理资源


app = FastAPI(
    title="EATING 后端 API",
    description="餐饮推荐系统后端",
    version="1.0.0",
    lifespan=lifespan,
    json_schema_kwargs={"json_encoders": {datetime: lambda dt: dt.isoformat()}}
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router, prefix="/api")
app.include_router(ingredients.router, prefix="/api")
app.include_router(recipes.router, prefix="/api")
app.include_router(recipes.router_search, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(admins.router, prefix="/api")
app.include_router(upload.router, prefix="/api")
app.include_router(chat.router, prefix="/api")

# 添加静态文件服务（上传的图片）
upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), settings.LOCAL_UPLOAD_DIR)
if os.path.exists(upload_dir):
    app.mount("/uploads", StaticFiles(directory=upload_dir), name="uploads")


@app.get("/")
async def root():
    return {"message": "EATING API 正在运行"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)