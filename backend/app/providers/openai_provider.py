"""
OpenAI Provider — 流式翻译 / 批量翻译实现。
"""
import logging
import time
import re
from typing import AsyncGenerator

from openai import AsyncOpenAI

from app.core.config import settings
from app.providers.base import TranslatorProvider

logger = logging.getLogger(__name__)
llm_logger = logging.getLogger("llm_requests")

_SINGLE_SYSTEM_TMPL = """\
你是一位专业翻译员。请将以下{source_lang}文本翻译成{target_lang}。
要求：
- 只输出译文，不加解释或额外内容
- 保持原文的语义和语气
{extra}"""

_BATCH_SYSTEM_TMPL = """\
你是一位专业翻译员。请将下列{source_lang}段落批量翻译成{target_lang}。
每段已按序编号，请严格按照相同编号格式逐行返回译文，格式为：
1. 译文
2. 译文
...
要求：
- 按编号顺序输出，每个编号占独立一行开头
- 只输出译文，不加任何解释
- 保持原段落的语义和语气
- 段落之间不要额外空行
{extra}"""


def _parse_numbered_output(text: str, expected: int) -> list[str]:
    """解析编号格式输出，支持多行段落译文。"""
    results: list[str] = [""] * expected
    current_idx: int | None = None
    current_lines: list[str] = []

    for line in text.split("\n"):
        m = re.match(r"^(\d+)\.\s*(.*)", line.strip())
        if m:
            if current_idx is not None:
                results[current_idx] = "\n".join(current_lines).strip()
            current_idx = int(m.group(1)) - 1
            current_lines = [m.group(2)]
        elif current_idx is not None:
            current_lines.append(line)

    if current_idx is not None:
        results[current_idx] = "\n".join(current_lines).strip()

    return results


def _build_extra_headers() -> dict:
    """
    当使用阿里云 DashScope 时，添加关闭安全审查的请求头。
    X-DashScope-DataInspection: disable  — 跳过输入内容安全检测
    """
    headers: dict = {}
    base_url = settings.openai_base_url or ""
    if "dashscope" in base_url or "aliyuncs" in base_url:
        headers["X-DashScope-DataInspection"] = "disable"
    return headers


def _masked_key_suffix(api_key: str) -> str:
    if not api_key:
        return "<empty>"
    return api_key[-6:]


class OpenAIProvider(TranslatorProvider):
    def __init__(self) -> None:
        headers = _build_extra_headers()
        self._client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            default_headers=headers,
        )
        logger.info(
            "provider.init base_url=%s model=%s api_key_suffix=%s dashscope_headers=%s",
            settings.openai_base_url,
            settings.default_model,
            _masked_key_suffix(settings.openai_api_key),
            ",".join(sorted(headers.keys())) or "<none>",
        )

    def _build_single_system(self, source_lang: str, target_lang: str, extra: str) -> str:
        return _SINGLE_SYSTEM_TMPL.format(
            source_lang=source_lang, target_lang=target_lang, extra=extra
        )

    def _build_batch_system(self, source_lang: str, target_lang: str, extra: str) -> str:
        return _BATCH_SYSTEM_TMPL.format(
            source_lang=source_lang, target_lang=target_lang, extra=extra
        )

    async def translate_stream(
        self,
        source_text: str,
        source_lang: str,
        target_lang: str,
        system_prompt: str = "",
    ) -> AsyncGenerator[str, None]:
        system = self._build_single_system(source_lang, target_lang, system_prompt)
        t0 = time.time()
        llm_logger.info(
            "=== translate_stream REQUEST ===\n"
            "model=%s  source_lang=%s  target_lang=%s\n"
            "system_prompt_len=%d  user_content_len=%d\n"
            "--- SYSTEM PROMPT ---\n%s\n"
            "--- USER CONTENT (first 2000 chars) ---\n%s\n"
            "--- END REQUEST ---",
            settings.default_model, source_lang, target_lang,
            len(system), len(source_text),
            system,
            source_text[:2000],
        )
        try:
            stream = await self._client.chat.completions.create(
                model=settings.default_model,
                temperature=settings.default_temperature,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": source_text},
                ],
                stream=True,
            )
            token_count = 0
            async for chunk in stream:
                delta = chunk.choices[0].delta.content
                if delta:
                    token_count += 1
                    yield delta
            elapsed = time.time() - t0
            llm_logger.info(
                "=== translate_stream DONE === tokens=%d elapsed=%.1fs",
                token_count, elapsed,
            )
        except Exception:
            elapsed = time.time() - t0
            logger.exception(
                "provider.translate_stream failed base_url=%s model=%s api_key_suffix=%s text_len=%s elapsed=%.1fs",
                settings.openai_base_url,
                settings.default_model,
                _masked_key_suffix(settings.openai_api_key),
                len(source_text),
                elapsed,
            )
            llm_logger.exception(
                "=== translate_stream FAILED === elapsed=%.1fs", elapsed,
            )
            raise

    async def translate_once(
        self,
        source_text: str,
        source_lang: str,
        target_lang: str,
        system_prompt: str = "",
    ) -> str:
        system = self._build_single_system(source_lang, target_lang, system_prompt)
        t0 = time.time()
        llm_logger.info(
            "=== translate_once REQUEST ===\n"
            "model=%s  system_len=%d  user_len=%d\n"
            "--- SYSTEM ---\n%s\n"
            "--- USER (first 2000) ---\n%s\n--- END ---",
            settings.default_model, len(system), len(source_text),
            system, source_text[:2000],
        )
        try:
            resp = await self._client.chat.completions.create(
                model=settings.default_model,
                temperature=settings.default_temperature,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": source_text},
                ],
            )
            result = resp.choices[0].message.content or ""
            elapsed = time.time() - t0
            usage = getattr(resp, 'usage', None)
            llm_logger.info(
                "=== translate_once DONE === result_len=%d elapsed=%.1fs usage=%s",
                len(result), elapsed, usage,
            )
            return result
        except Exception:
            elapsed = time.time() - t0
            logger.exception(
                "provider.translate_once failed base_url=%s model=%s elapsed=%.1fs",
                settings.openai_base_url, settings.default_model, elapsed,
            )
            llm_logger.exception("=== translate_once FAILED === elapsed=%.1fs", elapsed)
            raise

    async def translate_batch(
        self,
        texts: list[str],
        source_lang: str,
        target_lang: str,
        system_prompt: str = "",
    ) -> list[str]:
        if not texts:
            return []

        numbered_input = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(texts))
        system = self._build_batch_system(source_lang, target_lang, system_prompt)
        t0 = time.time()
        llm_logger.info(
            "=== translate_batch REQUEST ===\n"
            "model=%s  batch_size=%d  system_len=%d  user_len=%d\n"
            "--- SYSTEM ---\n%s\n"
            "--- USER (first 2000) ---\n%s\n--- END ---",
            settings.default_model, len(texts), len(system), len(numbered_input),
            system, numbered_input[:2000],
        )
        try:
            resp = await self._client.chat.completions.create(
                model=settings.default_model,
                temperature=settings.default_temperature,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": numbered_input},
                ],
            )
            raw = resp.choices[0].message.content or ""
            elapsed = time.time() - t0
            usage = getattr(resp, 'usage', None)
            llm_logger.info(
                "=== translate_batch DONE === result_len=%d elapsed=%.1fs usage=%s",
                len(raw), elapsed, usage,
            )
            return _parse_numbered_output(raw, len(texts))
        except Exception:
            elapsed = time.time() - t0
            logger.exception(
                "provider.translate_batch failed base_url=%s model=%s elapsed=%.1fs",
                settings.openai_base_url, settings.default_model, elapsed,
            )
            llm_logger.exception("=== translate_batch FAILED === elapsed=%.1fs", elapsed)
            raise


def get_provider() -> TranslatorProvider:
    return OpenAIProvider()
