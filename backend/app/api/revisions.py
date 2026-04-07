"""
路由：Revisions
PATCH /api/revisions/{revisionId}  — Accept 或 Reject
"""
import json

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db.session import get_session
from app.models.document import Document
from app.schemas.document import ApplyRevisionRequest, ApplyRevisionResponse, DiffOpOut, RevisionOut, SegmentOut
from app.services.revision_service import apply_revision

router = APIRouter(prefix="/api/revisions", tags=["revisions"])


def _seg_to_out(seg) -> SegmentOut:
    return SegmentOut(
        id=seg.id,
        documentId=seg.document_id,
        index=seg.index,
        paraType=seg.para_type,
        sourceHtml=getattr(seg, 'source_html', None),
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


@router.patch("/{revision_id}", response_model=ApplyRevisionResponse)
def patch_revision(
    revision_id: str,
    body: ApplyRevisionRequest,
    session: Session = Depends(get_session),
):
    # 获取 doc 语种信息用于写 EditRecord
    from app.models.document import SegmentRevision, Segment
    rev_obj = session.get(SegmentRevision, revision_id)
    seg_obj = session.get(Segment, rev_obj.segment_id) if rev_obj else None
    doc_obj = session.get(Document, seg_obj.document_id) if seg_obj else None

    seg, rev = apply_revision(
        session,
        revision_id,
        body.action,
        doc_obj.source_lang if doc_obj else "en",
        doc_obj.target_lang if doc_obj else "zh",
    )
    return ApplyRevisionResponse(segment=_seg_to_out(seg), revision=_rev_to_out(rev))
