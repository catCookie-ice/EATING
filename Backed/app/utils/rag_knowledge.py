"""
知识库解析工具

解析「常见疾病与对应忌口.txt」为结构化记录，供 RAG 检索使用。
"""

import re
from typing import List, Optional
from dataclasses import dataclass, field


@dataclass
class DiseaseRecord:
    """单条疾病忌口记录"""
    disease: str
    category: str
    restricted_foods: List[str] = field(default_factory=list)
    restriction_detail: str = ""
    notes: Optional[str] = None


# 子类别标记——这些行不是独立疾病，而是疾病的子分类描述
_SUB_CATEGORY_MARKERS = {
    "肉蛋水产", "蔬菜其他", "腌制/高脂肉类", "发物/刺激物",
    "热性便秘", "虚寒性便秘",
}


def parse_knowledge_base(file_path: str) -> List[DiseaseRecord]:
    """解析知识库文本文件"""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    lines = content.strip().split("\n")

    records: List[DiseaseRecord] = []
    current_category: str = ""
    current_disease: Optional[str] = None
    current_restrictions: List[str] = []
    current_detail_parts: List[str] = []
    current_notes: Optional[str] = None

    category_pattern = re.compile(r'^[一二三四五六七八九十]+、\s*(.*?)$')
    disease_pattern = re.compile(r'^([^：]+?)：')

    def _extract_foods(text: str) -> List[str]:
        """从文本中提取食物/忌口名称"""
        foods = []
        # 按中文顿号、逗号、分号分割
        for part in re.split(r'[、，,;；]', text):
            part = part.strip().rstrip("。.")
            if not part:
                continue
            # 跳过纯数字、括号注释
            if re.match(r'^\d+$', part):
                continue
            # 跳过 "等发物"、"等"这类尾缀
            part = re.sub(r'等.*$', '', part).strip()
            if not part:
                continue
            foods.append(part)
        return foods

    def _flush_disease():
        nonlocal current_disease, current_restrictions, current_detail_parts, current_notes
        if current_disease:
            full_detail = "".join(current_detail_parts).strip().strip("，。；,.; ")
            records.append(DiseaseRecord(
                disease=current_disease,
                category=current_category,
                restricted_foods=sorted(set(
                    f.strip() for f in current_restrictions if f.strip()
                )),
                restriction_detail=full_detail,
                notes=current_notes,
            ))
        current_disease = None
        current_restrictions = []
        current_detail_parts = []
        current_notes = None

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith("常见疾病") or line.startswith("---"):
            continue

        # 大类标题
        cat_match = category_pattern.match(line)
        if cat_match and line.endswith("疾病") or (
            cat_match and ("疾病" in line or "系统" in line)
        ):
            # Only match if it looks like a category header
            if re.match(r'^[一二三四五六七八九十]+、', line):
                _flush_disease()
                current_category = cat_match.group(1).strip()
                continue

        # 检查是否含冒号
        if "：" in line:
            disease_match = disease_pattern.match(line)
            if disease_match:
                name = disease_match.group(1).strip()

                # 判断是否为子类别标记（如 "肉蛋水产"、"蔬菜其他"）
                is_sub = False
                for marker in _SUB_CATEGORY_MARKERS:
                    if name == marker or name.startswith(marker):
                        is_sub = True
                        break

                if is_sub and current_disease:
                    # 追加到当前疾病
                    after = line[disease_match.end():].strip()
                    if after:
                        current_detail_parts.append(f"（{name}）{after}")
                        current_restrictions.extend(_extract_foods(after))
                    continue

                # 正常疾病行
                _flush_disease()
                # 清理序号前缀
                name = re.sub(r'^\d+[、.．]\s*', '', name)
                if not name:
                    continue
                current_disease = name

                after_colon = line[disease_match.end():].strip()
                if after_colon:
                    current_detail_parts.append(after_colon)
                    current_restrictions.extend(_extract_foods(after_colon))
                continue

        # 续行（无冒号或未被识别为疾病行）
        if current_disease:
            current_detail_parts.append(line)
            # 提取备注
            note_match = re.search(r'[（(]注[：:](.*?)[）)]', line)
            if note_match:
                current_notes = note_match.group(1).strip()
            current_restrictions.extend(_extract_foods(line))

    _flush_disease()
    return records


def build_chunk_text(record: DiseaseRecord) -> str:
    """构建用于向量化的文本块"""
    foods = "、".join(record.restricted_foods[:25])
    text = (
        f"疾病名称：{record.disease}\n"
        f"所属类别：{record.category}\n"
        f"忌口食物：{foods}"
    )
    if record.notes:
        text += f"\n备注：{record.notes}"
    return text


def search_by_disease_name(query: str, records: List[DiseaseRecord]) -> List[DiseaseRecord]:
    """通过疾病名称模糊匹配搜索"""
    q = query.lower()
    return [r for r in records if q in r.disease.lower()]


if __name__ == "__main__":
    import os
    test_path = os.path.join(os.path.dirname(__file__), "..", "resource",
                             "常见疾病与对应忌口.txt")
    test_path = os.path.abspath(test_path)
    records = parse_knowledge_base(test_path)
    print(f"共解析 {len(records)} 条疾病忌口记录\n")
    for i, r in enumerate(records, 1):
        foods = "、".join(r.restricted_foods[:6])
        suffix = "..." if len(r.restricted_foods) > 6 else ""
        print(f"{i:2d}. [{r.category}] {r.disease}: {foods}{suffix}")

    # 验证特定疾病
    print("\n--- 验证 ---")
    for name in ["哮喘", "腹胀", "便秘", "感冒"]:
        found = [r for r in records if r.disease == name]
        if found:
            r = found[0]
            print(f"\n{name} ({len(r.restricted_foods)} 种忌口):")
            print(f"  {', '.join(r.restricted_foods[:10])}...")
