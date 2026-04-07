"""
翻译 Provider 抽象基类。
所有具体 Provider 实现此接口。
"""
from abc import ABC, abstractmethod
from typing import AsyncGenerator


class TranslatorProvider(ABC):
    """
    translate_stream：流式翻译单句，逐 token yield 字符串片段。
    translate_once：单次完整翻译（用于改写/提取）。
    translate_batch：批量翻译多段落，单次 API 调用，返回译文列表。
    """

    @abstractmethod
    async def translate_stream(
        self,
        source_text: str,
        source_lang: str,
        target_lang: str,
        system_prompt: str = "",
    ) -> AsyncGenerator[str, None]:
        """Yield translation token chunks."""
        ...

    @abstractmethod
    async def translate_once(
        self,
        source_text: str,
        source_lang: str,
        target_lang: str,
        system_prompt: str = "",
    ) -> str:
        """Return full translation at once (used for rewrite / extraction)."""
        ...

    @abstractmethod
    async def translate_batch(
        self,
        texts: list[str],
        source_lang: str,
        target_lang: str,
        system_prompt: str = "",
    ) -> list[str]:
        """Translate a batch of texts in a single API call.

        Returns a list of translations corresponding to ``texts``.
        Missing items are returned as empty strings.
        """
        ...
