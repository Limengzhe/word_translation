"""
路由：Segments
PATCH /api/segments/{segmentId}/source   — 编辑原文
POST  /api/segments/{segmentId}/sync     — 单句同步翻译（SSE）
POST  /api/segments/{segmentId}/rewrite  — 模型改写
PATCH /api/segments/{segmentId}/target   — 用户编辑译文
"""
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from app.core.errors import AppError, ErrorCode
from app.db.session import get_session
from app.models.document import Segment, SourceStatusEnum
from app.models.document import RevisionProposerEnum
from app.providers import get_provider
from app.schemas.document import (
    DiffOpOut,
    PatchSegmentSourceResponse,
    PatchSegmentTargetResponse,
    PatchSourceRequest,
    PatchTargetRequest,
    RewriteRequest,
    RewriteResponse,
    SegmentOut,
    RevisionOut,
)
from app.services.revision_service import create_revision
from app.services.translation_service import stream_sync_segment
from app.services.prompt_builder import build_skill_prompt
from app.models.document import Document
from app.core.config import settings
import json

router = APIRouter(prefix="/api/segments", tags=["segments"])


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


def _rev_to_out(rev) -> RevisionOut:
    diff = None
    if rev.diff_json:
        try:
            diff = [DiffOpOut(**op) for op in json.loads(rev.diff_json)]
        except Exception:
            diff = None
    return RevisionOut(
        id=rev.id,
        segmentId=rev.segment_id,
        baseText=rev.base_text,
        proposedText=rev.proposed_text,
        proposer=rev.proposer.value,
        state=rev.state.value,
        createdAt=rev.created_at,
        diff=diff,
    )


@router.patch("/{segment_id}/source", response_model=PatchSegmentSourceResponse)
def patch_source(
    segment_id: str,
    body: PatchSourceRequest,
    session: Session = Depends(get_session),
):
    seg = session.get(Segment, segment_id)
    if not seg:
        raise AppError(ErrorCode.NOT_FOUND, "Segment not found", 404)
    if len(body.source_text) > settings.max_segment_chars:
        raise AppError(ErrorCode.SEGMENT_TOO_LONG, "Source text too long", 413)

    seg.source_text = body.source_text
    seg.source_status = SourceStatusEnum.source_edited
    session.add(seg)
    session.commit()
    session.refresh(seg)
    return PatchSegmentSourceResponse(segment=_seg_to_out(seg))


@router.post("/{segment_id}/sync")
async def sync_segment(
    segment_id: str,
    session: Session = Depends(get_session),
):
    """流式单句同步翻译（SSE），完成后自动创建 pending revision。"""
    provider = get_provider()
    seg = session.get(Segment, segment_id)
    if not seg:
        raise AppError(ErrorCode.NOT_FOUND, "Segment not found", 404)
    doc = session.get(Document, seg.document_id)

    collected_parts = []

    async def gen():
        nonlocal collected_parts
        proposed_text = ""
        async for chunk in stream_sync_segment(segment_id, session, provider):
            yield chunk
            # 解析 token 事件收集译文
            if chunk.startswith("event: token"):
                try:
                    data_line = [l for l in chunk.split("\n") if l.startswith("data:")]
                    if data_line:
                        payload = json.loads(data_line[0][5:])
                        proposed_text += payload.get("token", "")
                except Exception:
                    pass
            elif chunk.startswith("event: completed"):
                try:
                    data_line = [l for l in chunk.split("\n") if l.startswith("data:")]
                    if data_line:
                        payload = json.loads(data_line[0][5:])
                        proposed_text = payload.get("proposedText", proposed_text)
                except Exception:
                    pass

        # 翻译完成后创建 pending revision
        if proposed_text.strip():
            session.expire_all()
            seg2 = session.get(Segment, segment_id)
            if seg2 and not seg2.pending_revision_id:
                rev = create_revision(
                    session,
                    segment_id,
                    proposed_text.strip(),
                    RevisionProposerEnum.model,
                )
                data = json.dumps(
                    {"revisionId": rev.id, "proposedText": rev.proposed_text},
                    ensure_ascii=False,
                )
                yield f"event: revision_created\ndata: {data}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.post("/{segment_id}/rewrite", response_model=RewriteResponse)
async def rewrite_segment(
    segment_id: str,
    body: RewriteRequest,
    session: Session = Depends(get_session),
):
    seg = session.get(Segment, segment_id)
    if not seg:
        raise AppError(ErrorCode.NOT_FOUND, "Segment not found", 404)
    doc = session.get(Document, seg.document_id)
    if not doc:
        raise AppError(ErrorCode.NOT_FOUND, "Document not found", 404)

    provider = get_provider()
    system_extra = build_skill_prompt(session, doc.source_lang, doc.target_lang, body.style_preset)
    instruction_prefix = f"请根据以下要求改写译文，要求：{body.instruction}\n\n原文：{seg.source_text}\n当前译文：{seg.current_text}"

    result = await provider.translate_once(
        source_text=instruction_prefix,
        source_lang=doc.source_lang,
        target_lang=doc.target_lang,
        system_prompt=system_extra,
    )

    rev = create_revision(session, segment_id, result.strip(), RevisionProposerEnum.model)
    return RewriteResponse(revision=_rev_to_out(rev))


@router.patch("/{segment_id}/target", response_model=PatchSegmentTargetResponse)
def patch_target(
    segment_id: str,
    body: PatchTargetRequest,
    session: Session = Depends(get_session),
):
    rev = create_revision(
        session,
        segment_id,
        body.user_edited_text,
        RevisionProposerEnum.user,
    )
    return PatchSegmentTargetResponse(revision=_rev_to_out(rev))
