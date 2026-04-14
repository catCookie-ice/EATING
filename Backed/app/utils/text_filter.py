import re
from pathlib import Path
from typing import List


class TextFilter:
    """文本过滤器，用于过滤违禁词"""

    _blocked_words: set = set()
    _initialized: bool = False

    @classmethod
    def _load_blocked_words(cls) -> None:
        """加载违禁词库"""
        if cls._initialized:
            return

        words_file = Path(__file__).parent / "blocked_words.txt"
        if words_file.exists():
            with open(words_file, "r", encoding="utf-8") as f:
                for line in f:
                    word = line.strip()
                    if word and not line.startswith("#"):
                        cls._blocked_words.add(word)

        cls._initialized = True

    @classmethod
    def filter_text(cls, text: str) -> str:
        """过滤文本中的违禁词，替换为等长度的X

        Args:
            text: 待过滤的文本

        Returns:
            过滤后的文本
        """
        if not text:
            return text

        cls._load_blocked_words()

        result = text
        # 按长度降序排列违禁词，优先匹配最长词
        sorted_words = sorted(cls._blocked_words, key=len, reverse=True)

        for word in sorted_words:
            # 使用正则表达式进行不区分大小写的匹配
            pattern = re.compile(re.escape(word), re.IGNORECASE)
            # 替换为等长度的X
            replacement = "X" * len(word)
            result = pattern.sub(replacement, result)

        return result

    @classmethod
    def filter_text_list(cls, text_list: List[str]) -> List[str]:
        """过滤文本列表中的违禁词

        Args:
            text_list: 待过滤的文本列表

        Returns:
            过滤后的文本列表
        """
        if not text_list:
            return text_list
        return [cls.filter_text(text) for text in text_list]

    @classmethod
    def reload_blocked_words(cls) -> None:
        """重新加载违禁词库"""
        cls._blocked_words = set()
        cls._initialized = False
        cls._load_blocked_words()

    @classmethod
    def get_blocked_words(cls) -> set:
        """获取违禁词集合"""
        cls._load_blocked_words()
        return cls._blocked_words.copy()
