"""
知识库管理路由（仅 0 级管理员可用）

提供知识库文件的上传、列表、切换激活、删除、重建索引等管理功能。
"""

import os
import shutil
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from pydantic import BaseModel

from app.dependencies import require_level_0_admin
from app.models.admin import Admin
from app.utils.vector_store import (
    list_knowledge_bases,
    get_active_kb_info,
    rebuild_from_file,
    _get_kb_upload_dir,
    _get_default_kb_path,
    initialize_knowledge_base,
)
from app.config import settings

router = APIRouter(prefix="/admins/knowledge-base", tags=["管理员-知识库管理"])

# 允许的知识库文件类型
ALLOWED_KB_TYPES = {"text/plain", "text/plain; charset=utf-8"}
# 最大文件大小 (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024


class KBItem(BaseModel):
    """知识库条目"""
    name: str
    path: str
    is_default: bool
    is_active: bool
    records_count: int = 0


class KBListResponse(BaseModel):
    """知识库列表响应"""
    bases: List[KBItem]
    active: KBItem


class KBActivateRequest(BaseModel):
    """激活知识库请求"""
    name: str


# ── 工具函数 ────────────────────────────────────────────

def _safe_kb_name(name: str) -> str:
    """清理知识库名称，只保留安全字符"""
    safe = "".join(c for c in name if c.isalnum() or c in " _-.（）()（）（）")
    return safe.strip() or "untitled"


def _get_kb_dir(name: str) -> str:
    """获取某个上传知识库存放的目录路径"""
    return os.path.join(_get_kb_upload_dir(), name)


def _kb_exists(name: str) -> bool:
    """检查知识库名称是否已存在"""
    # 检查默认知识库
    default_name = settings.KB_DEFAULT_FILE.replace(".txt", "")
    if name == default_name:
        return True
    # 检查上传的知识库
    return os.path.exists(os.path.join(_get_kb_upload_dir(), name, "source.txt"))


# ── API 端点 ────────────────────────────────────────────

@router.get("/list", response_model=KBListResponse)
def list_bases(admin: Admin = Depends(require_level_0_admin)):
    """列出所有知识库"""
    active = get_active_kb_info()
    bases = list_knowledge_bases()

    return KBListResponse(
        bases=[KBItem(**b) for b in bases],
        active=KBItem(
            name=active.get("name", ""),
            path=active.get("path", ""),
            is_default=active.get("is_default", True),
            is_active=True,
            records_count=active.get("records_count", 0),
        ),
    )


@router.post("/upload")
async def upload_knowledge_base(
    file: UploadFile = File(..., description="知识库 TXT 文件"),
    admin: Admin = Depends(require_level_0_admin),
):
    """上传新的知识库 TXT 文件

    文件上传后自动解析并重建向量索引，新知识库立即生效。
    """
    # 验证文件类型
    content_type = file.content_type or ""
    if content_type not in ALLOWED_KB_TYPES and "text" not in content_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件类型: {content_type}，仅支持 TXT 文件",
        )

    # 读取文件内容
    file_content = await file.read()

    # 验证文件大小
    if len(file_content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件大小不能超过10MB，当前: {len(file_content) / 1024 / 1024:.2f}MB",
        )

    # 尝试 UTF-8 解码
    try:
        text = file_content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件编码不是 UTF-8，请使用 UTF-8 编码的 TXT 文件",
        )

    if not text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件内容为空",
        )

    # 生成知识库名称
    original_name = file.filename or "untitled"
    base_name = os.path.splitext(original_name)[0]
    kb_name = _safe_kb_name(base_name)

    # 检查是否已存在同名 KB
    if _kb_exists(kb_name):
        # 加时间戳后缀避免覆盖
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        kb_name = f"{kb_name}_{timestamp}"

    # 创建知识库目录并保存文件
    kb_dir = _get_kb_dir(kb_name)
    os.makedirs(kb_dir, exist_ok=True)
    dest_path = os.path.join(kb_dir, "source.txt")

    with open(dest_path, "wb") as f:
        f.write(file_content)

    # 重建向量索引并激活
    try:
        rebuild_from_file(kb_name, dest_path)
    except Exception as e:
        # 构建索引失败，清理文件
        shutil.rmtree(kb_dir, ignore_errors=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"知识库解析或索引构建失败: {str(e)}。文件格式可能不正确。",
        )

    return {
        "message": f"知识库「{kb_name}」上传并激活成功",
        "name": kb_name,
        "path": dest_path,
        "records_count": len(text.strip().split("\n")),
    }


@router.post("/activate")
def activate_knowledge_base(
    req: KBActivateRequest,
    admin: Admin = Depends(require_level_0_admin),
):
    """激活指定的知识库（切换到另一个已上传的知识库）"""
    name = req.name.strip()
    default_name = settings.KB_DEFAULT_FILE.replace(".txt", "")

    # 检查是否是默认知识库
    if name == default_name:
        kb_path = _get_default_kb_path()
        if not os.path.exists(kb_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"默认知识库文件不存在: {kb_path}",
            )
        rebuild_from_file(name, kb_path)
        return {"message": f"已切换到默认知识库「{name}」", "name": name}

    # 检查上传的知识库
    kb_path = os.path.join(_get_kb_upload_dir(), name, "source.txt")
    if not os.path.exists(kb_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"知识库「{name}」不存在",
        )

    rebuild_from_file(name, kb_path)
    return {"message": f"已切换到知识库「{name}」", "name": name}


@router.delete("/{name}")
def delete_knowledge_base(
    name: str,
    admin: Admin = Depends(require_level_0_admin),
):
    """删除上传的知识库（默认知识库不可删除）"""
    default_name = settings.KB_DEFAULT_FILE.replace(".txt", "")

    if name == default_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="默认知识库不可删除",
        )

    kb_dir = _get_kb_dir(name)
    if not os.path.exists(kb_dir):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"知识库「{name}」不存在",
        )

    # 检查是否当前激活的 KB
    active = get_active_kb_info()
    is_active = active.get("name") == name or active.get("path", "").startswith(kb_dir)

    # 删除目录
    shutil.rmtree(kb_dir)

    # 如果删除的是当前激活的 KB，回退到默认知识库
    if is_active:
        default_path = _get_default_kb_path()
        if os.path.exists(default_path):
            rebuild_from_file(settings.KB_DEFAULT_FILE.replace(".txt", ""), default_path)

    return {
        "message": f"知识库「{name}」已删除",
        "fallback_to_default": is_active,
    }


@router.post("/rebuild")
def rebuild_index(admin: Admin = Depends(require_level_0_admin)):
    """重建当前激活知识库的向量索引"""
    try:
        initialize_knowledge_base(force_rebuild=True)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"索引重建失败: {str(e)}",
        )

    active = get_active_kb_info()
    return {
        "message": f"知识库「{active['name']}」索引重建完成",
        "name": active["name"],
        "records_count": active.get("records_count", 0),
    }
