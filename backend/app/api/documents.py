"""
路由：Documents
POST /api/documents                        — 创建文档
GET  /api/documents/{docId}               — 获取文档 + segments
PATCH /api/documents/{docId}/full-html    — 保存编辑后的 HTML
POST /api/documents/{docId}/translate-full/stream — 全文流式翻译
GET  /api/documents/{docId}/download      — 下载译文 Word 文件
"""
import io
import json
import uuid as _uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response, StreamingResponse
from sqlmodel import Session, select

from app.core.errors import AppError, ErrorCode
from app.db.session import get_session
from app.models.document import Document, Segment, SourceStatusEnum, TargetStatusEnum
from app.providers import get_provider
from app.schemas.document import (
    CreateDocumentRequest,
    CreateDocumentResponse,
    DocumentOut,
    DocumentSettings,
    GetDocumentResponse,
    ParagraphIn,
    PatchFullHtmlRequest,
    SegmentOut,
    TranslateStreamRequest,
)
from app.services.image_service import extract_and_store_images
from app.services.segmentation_service import split_text
from app.services.translation_service import stream_translate_document, stream_translate_full_html

router = APIRouter(prefix="/api/documents", tags=["documents"])

VALID_PARA_TYPES = {"h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "blockquote", "pre"}


def _doc_to_out(doc: Document) -> DocumentOut:
    settings = doc.get_settings()
    return DocumentOut(
        id=doc.id,
        sourceLang=doc.source_lang,
        targetLang=doc.target_lang,
        createdAt=doc.created_at,
        updatedAt=doc.updated_at,
        settings=DocumentSettings(**settings) if settings else DocumentSettings(),
        fullSourceHtml=doc.full_source_html,
        fullTranslatedHtml=doc.full_translated_html,
    )


def _seg_to_out(seg: Segment) -> SegmentOut:
    return SegmentOut(
        id=seg.id,
        documentId=seg.document_id,
        index=seg.index,
        paraType=seg.para_type,
        sourceHtml=seg.source_html,
        sourceText=seg.source_text,
        syncedSourceText=seg.synced_source_text,
        currentText=seg.current_text,
        targetStatus=seg.target_status.value,
        sourceStatus=seg.source_status.value,
        pendingRevisionId=seg.pending_revision_id,
    )


def _build_paragraphs(body: CreateDocumentRequest) -> list[ParagraphIn]:
    if body.paragraphs:
        return [
            ParagraphIn(
                text=p.text.strip(),
                paraType=p.para_type if p.para_type in VALID_PARA_TYPES else "p",
                sourceHtml=p.source_html,
            )
            for p in body.paragraphs
            if p.text.strip()
        ]
    if body.source_text:
        return [
            ParagraphIn(text=t, paraType="p")
            for t in split_text(body.source_text)
            if t.strip()
        ]
    return []


@router.post("", response_model=CreateDocumentResponse)
def create_document(
    body: CreateDocumentRequest,
    session: Session = Depends(get_session),
):
    if not body.full_source_html and not body.source_text:
        raise AppError(ErrorCode.VALIDATION_ERROR, "No content found in request", 422)

    pre_id = f"doc_{_uuid.uuid4().hex[:12]}"

    full_html = body.full_source_html
    if full_html:
        full_html = extract_and_store_images(full_html, pre_id)

    doc = Document(
        id=pre_id,
        source_lang=body.source_lang,
        target_lang=body.target_lang,
        settings_json=json.dumps(body.settings.model_dump(by_alias=False), ensure_ascii=False),
        full_source_html=full_html,
    )
    session.add(doc)
    session.commit()
    session.refresh(doc)

    return CreateDocumentResponse(
        document=_doc_to_out(doc),
        segments=[],
    )


@router.get("/{doc_id}", response_model=GetDocumentResponse)
def get_document(doc_id: str, session: Session = Depends(get_session)):
    doc = session.get(Document, doc_id)
    if not doc:
        raise AppError(ErrorCode.NOT_FOUND, "Document not found", 404)
    segs = session.exec(
        select(Segment)
        .where(Segment.document_id == doc_id)
        .order_by(Segment.index)
    ).all()
    return GetDocumentResponse(
        document=_doc_to_out(doc),
        segments=[_seg_to_out(s) for s in segs],
    )


@router.patch("/{doc_id}/full-html", response_model=DocumentOut)
def patch_full_html(
    doc_id: str,
    body: PatchFullHtmlRequest,
    session: Session = Depends(get_session),
):
    """保存用户在编辑器中直接修改的 HTML 内容。"""
    doc = session.get(Document, doc_id)
    if not doc:
        raise AppError(ErrorCode.NOT_FOUND, "Document not found", 404)

    if body.full_source_html is not None:
        doc.full_source_html = extract_and_store_images(body.full_source_html, doc_id)
    if body.full_translated_html is not None:
        doc.full_translated_html = extract_and_store_images(body.full_translated_html, doc_id)
    doc.updated_at = datetime.utcnow()

    session.add(doc)
    session.commit()
    session.refresh(doc)
    return _doc_to_out(doc)


@router.post("/{doc_id}/translate/stream")
async def translate_stream(
    doc_id: str,
    body: Optional[TranslateStreamRequest] = None,
    session: Session = Depends(get_session),
):
    style = body.style_preset if body else None
    provider = get_provider()

    async def gen():
        async for chunk in stream_translate_document(doc_id, session, provider, style):
            yield chunk

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{doc_id}/translate-full/stream")
async def translate_full_stream(
    doc_id: str,
    body: Optional[TranslateStreamRequest] = None,
    session: Session = Depends(get_session),
):
    """全文 HTML 翻译：一次 LLM 调用，流式输出翻译 HTML token。"""
    style = body.style_preset if body else None
    provider = get_provider()

    async def gen():
        async for chunk in stream_translate_full_html(doc_id, session, provider, style):
            yield chunk

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{doc_id}/download")
def download_docx(
    doc_id: str,
    which: str = Query(default="translated"),
    session: Session = Depends(get_session),
):
    """将 HTML 转为 Word (.docx) 文件下载。which=source 下载原文，translated 下载译文。"""
    from app.services.docx_export import html_to_docx

    if which not in ("source", "translated"):
        raise AppError(ErrorCode.VALIDATION_ERROR, "which must be 'source' or 'translated'", 422)

    doc = session.get(Document, doc_id)
    if not doc:
        raise AppError(ErrorCode.NOT_FOUND, "Document not found", 404)

    html = doc.full_translated_html if which == "translated" else doc.full_source_html
    if not html:
        raise AppError(ErrorCode.VALIDATION_ERROR, f"No {which} HTML available", 422)

    buf = html_to_docx(html)
    filename = f"{which}_{doc_id}.docx"
    return Response(
        content=buf.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
