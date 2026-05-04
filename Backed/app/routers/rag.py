"""
RAG 知识库查询路由

提供疾病忌口知识库的检索接口，支持向量语义检索和疾病名称精确匹配。
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.dependencies import get_current_user
from app.models.person import Person
from app.utils.vector_store import query_knowledge, initialize_knowledge_base
from app.utils.rag_knowledge import search_by_disease_name, build_chunk_text
from app.config import settings

router = APIRouter(prefix="/rag", tags=["RAG 知识库"])


class RAGQueryRequest(BaseModel):
    """RAG 查询请求"""
    query: str
    top_k: int = 5


class RAGRecord(BaseModel):
    """RAG 查询结果中的单条记录"""
    disease: str
    category: str
    restricted_foods: List[str]
    restriction_detail: str
    notes: Optional[str] = None
    similarity: float = 0.0


class RAGQueryResponse(BaseModel):
    """RAG 查询响应"""
    query: str
    results: List[RAGRecord]
    total: int


@router.post("/query", response_model=RAGQueryResponse)
async def query(
    request: RAGQueryRequest,
    current_user: Person = Depends(get_current_user),
):
    """
    向量语义检索——根据用户输入的自然语言查询，检索最相关的疾病忌口信息。

    例如查询 "糖尿病人能吃什么"、"咳嗽了要避免什么" 等。
    """
    # 确保知识库已初始化
    initialize_knowledge_base()

    top_k = min(max(request.top_k, 1), 20)

    # 向量检索
    results = query_knowledge(
        query=request.query,
        top_k=top_k,
        threshold=settings.RAG_SIMILARITY_THRESHOLD,
    )

    records = [
        RAGRecord(
            disease=r.disease,
            category=r.category,
            restricted_foods=r.restricted_foods,
            restriction_detail=r.restriction_detail,
            notes=r.notes,
            similarity=round(score, 4),
        )
        for r, score in results
    ]

    return RAGQueryResponse(
        query=request.query,
        results=records,
        total=len(records),
    )


@router.get("/search", response_model=RAGQueryResponse)
async def search_by_name(
    disease: str = Query(..., description="疾病名称，支持模糊匹配"),
    current_user: Person = Depends(get_current_user),
):
    """
    疾病名称精确/模糊匹配——根据疾病名称直接查找对应的忌口信息。

    比向量检索更精确，但需要疾病名称匹配。例如 "感冒"、"糖尿病" 等。
    """
    from app.utils.rag_knowledge import parse_knowledge_base
    import os

    kb_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "resource", "常见疾病与对应忌口.txt",
    )
    all_records = parse_knowledge_base(kb_path)
    matched = search_by_disease_name(disease, all_records)

    return RAGQueryResponse(
        query=disease,
        results=[
            RAGRecord(
                disease=r.disease,
                category=r.category,
                restricted_foods=r.restricted_foods,
                restriction_detail=r.restriction_detail,
                notes=r.notes,
                similarity=1.0,
            )
            for r in matched
        ],
        total=len(matched),
    )


@router.post("/context", response_model=str)
async def get_rag_context(
    request: RAGQueryRequest,
    current_user: Person = Depends(get_current_user),
):
    """
    获取格式化后的 RAG 上下文文本——直接返回适合拼接到 AI 提示词中的文本块。

    用于 AI 对话时检索知识库并注入上下文。
    """
    initialize_knowledge_base()

    top_k = min(max(request.top_k, 1), 10)
    results = query_knowledge(
        query=request.query,
        top_k=top_k,
        threshold=settings.RAG_SIMILARITY_THRESHOLD,
    )

    if not results:
        return ""

    lines = ["以下是与用户问题相关的疾病忌口知识：\n"]
    for i, (record, score) in enumerate(results, 1):
        chunk = build_chunk_text(record)
        lines.append(f"{i}. [相关度 {score:.2f}]")
        lines.append(f"   {chunk}")
        lines.append("")

    return "\n".join(lines)
