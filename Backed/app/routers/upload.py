"""文件上传路由"""
import os
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from typing import Optional

from app.dependencies import get_current_user
from app.models.person import Person
from app.utils.storage import get_storage, StorageService
from app.config import settings, StorageType

router = APIRouter(prefix="/upload", tags=["文件上传"])

# 允许的图片类型
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp", "image/bmp"}
# 最大图片大小 (5MB)
MAX_FILE_SIZE = 5 * 1024 * 1024


@router.post("/image")
async def upload_image(
    file: UploadFile = File(..., description="图片文件"),
    person: Person = Depends(get_current_user),
    file_type: str = "other"
):
    """上传图片文件

    Args:
        file_type: 文件类型，可选 avatar/cover/other
    返回图片URL地址，支持头像、封面等场景
    """
    # 验证文件类型
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的图片类型: {file.content_type}。支持的类型: jpeg, png, gif, webp, bmp"
        )

    # 读取文件内容
    file_content = await file.read()

    # 验证文件大小
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"图片大小不能超过5MB，当前大小: {len(file_content) / 1024 / 1024:.2f}MB"
        )

    # 获取存储服务并上传
    storage = get_storage()
    file_url = storage.upload(file_content, filename=file.filename or "image.jpg", file_type=file_type)

    return {
        "url": file_url,
        "filename": file.filename,
        "size": len(file_content),
        "content_type": file.content_type
    }


@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(..., description="头像图片"),
    person: Person = Depends(get_current_user)
):
    """上传用户头像

    返回头像的URL地址
    """
    return await upload_image(file, person, "avatar")


@router.post("/cover")
async def upload_cover(
    file: UploadFile = File(..., description="封面图片"),
    person: Person = Depends(get_current_user)
):
    """上传封面图片

    返回封面的URL地址，可用于食材或食谱封面
    """
    return await upload_image(file, person, "cover")


@router.get("/test")
async def test_storage():
    """测试存储服务是否可用"""
    try:
        storage = get_storage()
        storage_type = settings.STORAGE_TYPE

        # 检查云存储配置
        cloud_configured = all([
            settings.COS_SECRET_ID,
            settings.COS_SECRET_KEY,
            settings.COS_BUCKET,
            settings.COS_REGION
        ])

        return {
            "storage_type": storage_type,
            "cloud_configured": cloud_configured,
            "local_upload_dir": settings.LOCAL_UPLOAD_DIR,
            "status": "ok"
        }
    except Exception as e:
        return {
            "storage_type": settings.STORAGE_TYPE,
            "status": "error",
            "error": str(e)
        }
