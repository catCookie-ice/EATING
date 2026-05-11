"""
向量存储与检索服务

使用 sentence-transformers 将文本转为向量，基于 numpy 实现余弦相似度检索。
支持多个知识库源文件，可通过 .active 文件动态切换。
"""

import os
import json
import pickle
import numpy as np
from typing import List, Tuple, Optional, Any

from app.config import settings
from app.utils.rag_knowledge import DiseaseRecord, build_chunk_text


# 路径常量
_APP_DIR = os.path.dirname(os.path.dirname(__file__))
_RESOURCE_DIR = os.path.join(_APP_DIR, "resource")
_VECTOR_CACHE_DIR = os.path.join(_APP_DIR, ".vector_cache")
_EMBEDDING_FILE = os.path.join(_VECTOR_CACHE_DIR, "embeddings.npy")
_RECORDS_FILE = os.path.join(_VECTOR_CACHE_DIR, "records.pkl")
_INDEX_FILE = os.path.join(_VECTOR_CACHE_DIR, "index_map.json")
_ACTIVE_KB_FILE = os.path.join(_VECTOR_CACHE_DIR, "active_kb.json")


def _get_kb_upload_dir() -> str:
    """获取上传知识库存放目录的绝对路径"""
    return os.path.join(_RESOURCE_DIR, settings.KB_UPLOAD_DIR)


def _get_default_kb_path() -> str:
    """获取默认知识库文件路径"""
    return os.path.join(_RESOURCE_DIR, settings.KB_DEFAULT_FILE)


# ── 知识点激活管理 ───────────────────────────────────────

def get_active_kb_info() -> dict:
    """获取当前激活的知识库信息

    Returns:
        {"name": str, "path": str, "is_default": bool, "records_count": int}
    """
    active = {"name": settings.KB_DEFAULT_FILE, "path": _get_default_kb_path(),
              "is_default": True, "records_count": 0}

    if os.path.exists(_ACTIVE_KB_FILE):
        try:
            with open(_ACTIVE_KB_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            if os.path.exists(saved.get("path", "")):
                active.update(saved)
        except Exception:
            pass

    # 补充记录数
    if os.path.exists(_RECORDS_FILE):
        try:
            with open(_INDEX_FILE, "r", encoding="utf-8") as f:
                meta = json.load(f)
                active["records_count"] = meta.get("num_records", 0)
        except Exception:
            pass

    return active


def set_active_kb(name: str, file_path: str):
    """设置激活的知识库

    Args:
        name: 知识库名称
        file_path: 文件绝对路径
    """
    os.makedirs(_VECTOR_CACHE_DIR, exist_ok=True)
    with open(_ACTIVE_KB_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "name": name,
            "path": file_path,
            "is_default": False,
        }, f, ensure_ascii=False, indent=2)


def list_knowledge_bases() -> List[dict]:
    """列出所有可用的知识库

    Returns:
        [{"name": str, "path": str, "is_default": bool, "records_count": int, "is_active": bool}, ...]
    """
    active = get_active_kb_info()
    bases = []

    # 默认知识库
    default_path = _get_default_kb_path()
    if os.path.exists(default_path):
        bases.append({
            "name": settings.KB_DEFAULT_FILE.replace(".txt", ""),
            "path": default_path,
            "is_default": True,
            "is_active": active.get("name") == settings.KB_DEFAULT_FILE
                            or active.get("path") == default_path,
        })

    # 上传的知识库
    upload_dir = _get_kb_upload_dir()
    if os.path.exists(upload_dir):
        for item in sorted(os.listdir(upload_dir)):
            kb_dir = os.path.join(upload_dir, item)
            if os.path.isdir(kb_dir):
                source_file = os.path.join(kb_dir, "source.txt")
                if os.path.exists(source_file):
                    bases.append({
                        "name": item,
                        "path": source_file,
                        "is_default": False,
                        "is_active": active.get("name") == item
                                        or active.get("path") == source_file,
                    })

    return bases


# ── 向量存储类 ──────────────────────────────────────────

class VectorStore:
    """向量存储检索器

    基于 sentence-transformers 生成嵌入向量，使用 numpy 进行余弦相似度检索。
    """

    def __init__(
        self,
        model_name: str = "shibing624/text2vec-base-chinese",
        device: str = "cpu",
    ):
        self.model_name = model_name
        self.device = device
        self._model: Optional[Any] = None
        self._embeddings: Optional[np.ndarray] = None
        self._records: List[DiseaseRecord] = []
        self._loaded = False

    # ── 模型管理 ──────────────────────────────────────────

    @property
    def model(self) -> "SentenceTransformer":
        if self._model is None:
            # 延迟导入 sentence-transformers（避免启动时加载 PyTorch）
            # === HuggingFace 镜像/超时设置 ===
            if "HF_ENDPOINT" not in os.environ:
                os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
            os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = os.environ.get("HF_HUB_DOWNLOAD_TIMEOUT", "10")
            os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

            from sentence_transformers import SentenceTransformer

            # 策略1: 离线模式（模型已缓存，无网络请求）
            try:
                os.environ["TRANSFORMERS_OFFLINE"] = "1"
                os.environ["HF_HUB_OFFLINE"] = "1"
                self._model = SentenceTransformer(
                    self.model_name,
                    device=self.device,
                )
                return self._model
            except OSError:
                pass

            # 策略2: 国内镜像（首次下载用）
            os.environ.pop("TRANSFORMERS_OFFLINE", None)
            os.environ.pop("HF_HUB_OFFLINE", None)
            os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
            try:
                self._model = SentenceTransformer(
                    self.model_name,
                    device=self.device,
                )
            except OSError as e:
                raise RuntimeError(
                    f"无法加载嵌入模型 {self.model_name}。\n"
                    f"请确保网络可访问 hf-mirror.com，或模型已缓存到本地。\n"
                    f"错误: {e}"
                )
        return self._model

    @property
    def dim(self) -> int:
        """向量维度"""
        if self._embeddings is not None and len(self._embeddings) > 0:
            return self._embeddings.shape[1]
        return 768

    # ── 核心操作 ──────────────────────────────────────────

    def encode(self, texts: List[str]) -> np.ndarray:
        """将文本列表转为向量"""
        return self.model.encode(
            texts,
            convert_to_numpy=True,
            show_progress_bar=False,
            normalize_embeddings=True,
        )

    def build_index(self, records: List[DiseaseRecord]):
        """构建向量索引"""
        texts = [build_chunk_text(r) for r in records]
        self._embeddings = self.encode(texts)
        self._records = records
        self._loaded = True

    def search(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.3,
    ) -> List[Tuple[DiseaseRecord, float]]:
        """检索最相关的疾病忌口记录"""
        if not self._loaded or self._embeddings is None:
            return []

        query_vec = self.encode([query])
        scores = np.dot(self._embeddings, query_vec.T).flatten()

        top_indices = np.argsort(scores)[::-1]

        results = []
        for idx in top_indices:
            score = float(scores[idx])
            if score < threshold:
                continue
            results.append((self._records[idx], score))
            if len(results) >= top_k:
                break

        return results

    # ── 缓存读写 ──────────────────────────────────────────

    def save_cache(self):
        """将索引保存到磁盘缓存"""
        os.makedirs(_VECTOR_CACHE_DIR, exist_ok=True)

        if self._embeddings is not None:
            np.save(_EMBEDDING_FILE, self._embeddings)

        with open(_RECORDS_FILE, "wb") as f:
            pickle.dump(self._records, f)

        with open(_INDEX_FILE, "w", encoding="utf-8") as f:
            json.dump({
                "model_name": self.model_name,
                "num_records": len(self._records),
                "dim": self.dim,
            }, f, ensure_ascii=False, indent=2)

    def load_cache(self) -> bool:
        """从磁盘缓存加载索引"""
        if not os.path.exists(_EMBEDDING_FILE) or not os.path.exists(_RECORDS_FILE):
            return False

        try:
            self._embeddings = np.load(_EMBEDDING_FILE)
            with open(_RECORDS_FILE, "rb") as f:
                self._records = pickle.load(f)
            self._loaded = True
            return True
        except Exception as e:
            print(f"[VectorStore] 缓存加载失败: {e}")
            return False


# ── 全局单例 ────────────────────────────────────────────

_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """获取全局 VectorStore 单例（惰性初始化）"""
    global _store
    if _store is None:
        _store = VectorStore(
            model_name=settings.EMBEDDING_MODEL,
        )
    return _store


def initialize_knowledge_base(force_rebuild: bool = False):
    """初始化知识库向量索引

    优先从缓存加载。如果激活的知识库与缓存不一致则强制重建。

    Args:
        force_rebuild: 是否强制重建
    """
    from app.utils.rag_knowledge import parse_knowledge_base

    store = get_vector_store()

    # 获取当前激活的知识库文件
    active = get_active_kb_info()
    kb_path = active["path"]

    # 尝试从缓存加载（非强制重建时）
    if not force_rebuild and store.load_cache():
        # 验证缓存与激活的 KB 一致
        if os.path.exists(_INDEX_FILE):
            try:
                with open(_INDEX_FILE, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                cached_path = meta.get("source_path", "")
                if cached_path == kb_path:
                    return
                else:
                    print(f"[VectorStore] 知识库已切换 ({cached_path} → {kb_path})，重新构建索引")
            except Exception:
                pass
        else:
            return

    # 重新构建
    if not os.path.exists(kb_path):
        print(f"[VectorStore] 知识库文件不存在: {kb_path}，回退到默认知识库")
        kb_path = _get_default_kb_path()
        if not os.path.exists(kb_path):
            raise FileNotFoundError(f"默认知识库文件也不存在: {kb_path}")

    records = parse_knowledge_base(kb_path)
    store.build_index(records)
    store.save_cache()

    # 记录当前构建的源路径到缓存元信息
    with open(_INDEX_FILE, "r", encoding="utf-8") as f:
        meta = json.load(f)
    meta["source_path"] = kb_path
    with open(_INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"[VectorStore] 知识库 `{active['name']}` 初始化完成（{len(records)} 条记录，维度: {store.dim}）")


def rebuild_from_file(kb_name: str, file_path: str):
    """从指定文件重建向量索引并激活

    Args:
        kb_name: 知识库名称
        file_path: TXT 文件绝对路径
    """
    from app.utils.rag_knowledge import parse_knowledge_base

    # 设置激活的 KB
    set_active_kb(kb_name, file_path)

    # 强制重建
    initialize_knowledge_base(force_rebuild=True)


def query_knowledge(
    query: str,
    top_k: int = 5,
    threshold: float = 0.3,
) -> List[Tuple[DiseaseRecord, float]]:
    """查询知识库（快捷入口）"""
    store = get_vector_store()
    if not store._loaded:
        initialize_knowledge_base()
    return store.search(query, top_k=top_k, threshold=threshold)
