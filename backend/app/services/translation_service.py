"""
翻译服务：全文 HTML 翻译（SSE）/ 全文段落批量翻译（SSE）/ 单句同步翻译。

全文 HTML 翻译策略（stream_translate_full_html）：
  使用 translate_once（非流式单次调用）将完整 HTML 整体发给 LLM。
  LLM 看到完整文档结构和上下文，稳定可靠，不受 DashScope 流式限制影响。
  SSE 事件：started → completed / error

段落批量翻译策略（stream_translate_document）：
  将所有段落一次 translate_batch 调用，批量翻译后逐段推 segment SSE 事件。
"""
import json
import logging
import re
from typing import AsyncGenerator

from sqlmodel import Session, select

from app.core.errors import AppError, ErrorCode
from app.models.document import Document, Segment, SourceStatusEnum, TargetStatusEnum
from app.providers.base import TranslatorProvider
from app.services.prompt_builder import build_skill_prompt

logger = logging.getLogger(__name__)



def _make_seg_event(seg: Segment) -> str:
    data = json.dumps(
        {
            "segmentId": seg.id,
            "index": seg.index,
            "currentText": seg.current_text,
            "status": seg.target_status.value,
        },
        ensure_ascii=False,
    )
    return f"event: segment\ndata: {data}\n\n"


def _make_event(event: str, payload: dict) -> str:
    data = json.dumps(payload, ensure_ascii=False)
    return f"event: {event}\ndata: {data}\n\n"


async def stream_translate_document(
    doc_id: str,
    session: Session,
    provider: TranslatorProvider,
    style_preset: str | None = None,
) -> AsyncGenerator[str, None]:
    """
    全文批量翻译：将段落分组，每组一次 LLM 调用，批量翻译后推送 SSE segment 事件。
    相比逐句翻译，大幅减少 API 调用次数，翻译上下文更完整。
    """
    doc = session.get(Document, doc_id)
    if not doc:
        raise AppError(ErrorCode.NOT_FOUND, "Document not found", 404)

    segments = session.exec(
        select(Segment)
        .where(Segment.document_id == doc_id)
        .order_by(Segment.index)
    ).all()

    system_extra = build_skill_prompt(
        session, doc.source_lang, doc.target_lang, style_preset
    )

    logger.info(
        "translate_document.start doc_id=%s total_segments=%s source_lang=%s target_lang=%s",
        doc_id,
        len(segments),
        doc.source_lang,
        doc.target_lang,
    )

    yield _make_event("started", {"docId": doc_id, "total": len(segments)})

    texts = [seg.source_text for seg in segments]
    try:
        # 一次调用翻译所有段落，保留完整文档上下文
        translations = await provider.translate_batch(
            texts,
            doc.source_lang,
            doc.target_lang,
            system_extra,
        )
    except Exception as exc:
        logger.exception("translate_document.failed doc_id=%s", doc_id)
        yield _make_event(
            "error",
            {"code": ErrorCode.PROVIDER_ERROR.value, "message": str(exc)},
        )
        yield _make_event("completed", {"docId": doc_id, "translated": 0})
        return

    translated = 0
    for seg, translation in zip(segments, translations):
        if not translation:
            yield _make_event(
                "error",
                {
                    "code": ErrorCode.PROVIDER_ERROR.value,
                    "message": "Empty translation returned",
                    "segmentId": seg.id,
                },
            )
            continue

        seg.current_text = translation
        seg.synced_source_text = seg.source_text
        seg.target_status = TargetStatusEnum.machine
        seg.source_status = SourceStatusEnum.clean
        session.add(seg)
        session.commit()
        session.refresh(seg)

        translated += 1
        yield _make_seg_event(seg)

    logger.info("translate_document.completed doc_id=%s translated=%s", doc_id, translated)
    yield _make_event("completed", {"docId": doc_id, "translated": translated})



# ─── 全文 HTML 翻译 ───────────────────────────────────────────────────────────

_HTML_TRANSLATE_EXTRA = """\
这是一段 HTML 文档，请：
- 完整保留所有 HTML 标签及其属性，不得增删或修改标签
- 只翻译标签之间的文字内容，不翻译属性值
- 所有 <!--IMG_PLACEHOLDER_N--> 注释必须原样保留在原位置，不做任何修改
- 直接输出完整翻译后的 HTML，不加任何解释"""

_IMG_RE = re.compile(r'<img\b[^>]*/?>', re.IGNORECASE)


def _strip_images(html: str) -> tuple[str, list[str]]:
    """将 <img> 标签替换为占位注释，返回 (精简 HTML, 原始 img 列表)。"""
    imgs: list[str] = []
    def _replace(m: re.Match) -> str:
        idx = len(imgs)
        imgs.append(m.group(0))
        return f"<!--IMG_PLACEHOLDER_{idx}-->"
    stripped = _IMG_RE.sub(_replace, html)
    return stripped, imgs


def _restore_images(html: str, imgs: list[str]) -> str:
    """将占位注释还原为原始 <img> 标签。"""
    for idx, img_tag in enumerate(imgs):
        html = html.replace(f"<!--IMG_PLACEHOLDER_{idx}-->", img_tag)
    return html


async def stream_translate_full_html(
    doc_id: str,
    session: Session,
    provider: TranslatorProvider,
    style_preset: str | None = None,
) -> AsyncGenerator[str, None]:
    """
    全文 HTML 流式翻译：
    - 翻译前将 <img> 替换为占位符（避免 base64 超长数据发给 LLM）
    - 流式逐 token 返回，前端实时渲染
    - 翻译完成后将占位符还原为原始 <img>
    - SSE 事件：started → token* → completed / error
    """
    from datetime import datetime as _dt

    doc = session.get(Document, doc_id)
    if not doc:
        raise AppError(ErrorCode.NOT_FOUND, "Document not found", 404)

    if not doc.full_source_html:
        raise AppError(ErrorCode.VALIDATION_ERROR, "Document has no full_source_html", 422)

    skill_extra = build_skill_prompt(
        session, doc.source_lang, doc.target_lang, style_preset
    )
    system_extra = _HTML_TRANSLATE_EXTRA + ("\n" + skill_extra if skill_extra else "")

    # 翻译前剥离图片，减小发送给 LLM 的数据量
    stripped_html, imgs = _strip_images(doc.full_source_html)

    logger.info(
        "translate_full_html.start doc_id=%s source_lang=%s target_lang=%s "
        "original_len=%s stripped_len=%s images=%s",
        doc_id,
        doc.source_lang,
        doc.target_lang,
        len(doc.full_source_html),
        len(stripped_html),
        len(imgs),
    )

    yield _make_event("started", {"docId": doc_id})

    try:
        collected = ""
        async for chunk in provider.translate_stream(
            stripped_html,
            doc.source_lang,
            doc.target_lang,
            system_extra,
        ):
            collected += chunk
            yield _make_event("token", {"token": chunk})

        translated_html = collected.strip()
        if not translated_html:
            yield _make_event("error", {"code": "EMPTY", "message": "LLM returned empty translation"})
            return

        # 还原图片
        translated_html = _restore_images(translated_html, imgs)

        doc.full_translated_html = translated_html
        doc.updated_at = _dt.utcnow()
        session.add(doc)
        session.commit()

        logger.info(
            "translate_full_html.completed doc_id=%s translated_html_len=%s",
            doc_id,
            len(doc.full_translated_html),
        )
        yield _make_event("completed", {"docId": doc_id, "translatedHtml": translated_html})

    except Exception as exc:
        logger.exception("translate_full_html.failed doc_id=%s", doc_id)
        yield _make_event(
            "error",
            {"code": ErrorCode.PROVIDER_ERROR.value, "message": str(exc)},
        )


async def stream_sync_segment(
    segment_id: str,
    session: Session,
    provider: TranslatorProvider,
    style_preset: str | None = None,
) -> AsyncGenerator[str, None]:
    """
    单句同步翻译（SyncTranslation）：流式 token 推送，完成后生成 pending revision。
    """
    seg = session.get(Segment, segment_id)
    if not seg:
        raise AppError(ErrorCode.NOT_FOUND, "Segment not found", 404)

    doc = session.get(Document, seg.document_id)
    if not doc:
        raise AppError(ErrorCode.NOT_FOUND, "Document not found", 404)

    # 标记 syncing
    seg.source_status = SourceStatusEnum.syncing
    session.add(seg)
    session.commit()

    system_extra = build_skill_prompt(
        session, doc.source_lang, doc.target_lang, style_preset
    )

    yield _make_event("started", {"segmentId": segment_id})

    try:
        logger.info("sync_segment.start segment_id=%s doc_id=%s", segment_id, doc.id)
        collected = ""
        async for chunk in provider.translate_stream(
            seg.source_text,
            doc.source_lang,
            doc.target_lang,
            system_extra,
        ):
            collected += chunk
            yield _make_event("token", {"segmentId": segment_id, "token": chunk})

        new_text = collected.strip()
        yield _make_event(
            "completed",
            {"segmentId": segment_id, "proposedText": new_text},
        )

        # 由调用方（router）在 SSE 结束后创建 revision；这里只更新状态
        seg.source_status = SourceStatusEnum.clean
        seg.synced_source_text = seg.source_text
        session.add(seg)
        session.commit()

        logger.info("sync_segment.completed segment_id=%s", segment_id)
    except Exception as exc:
        logger.exception("sync_segment.failed segment_id=%s", segment_id)
        seg.source_status = SourceStatusEnum.source_edited
        session.add(seg)
        session.commit()
        yield _make_event(
            "fatal",
            {"code": ErrorCode.PROVIDER_ERROR.value, "message": str(exc)},
        )
