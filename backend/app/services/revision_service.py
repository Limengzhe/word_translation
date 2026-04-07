"""
修订服务：创建 / 应用 / 拒绝 SegmentRevision，Accept 时写 EditRecord。
"""
import json
from typing import List

from sqlmodel import Session

from app.core.errors import AppError, ErrorCode
from app.models.document import (
    RevisionProposerEnum,
    RevisionStateEnum,
    Segment,
    SegmentRevision,
    TargetStatusEnum,
)
from app.models.skill import EditRecord
from app.schemas.document import DiffOpOut


# ── diff（字符级，轻量实现）────────────────────────────────────────────────────

def _compute_diff(base: str, proposed: str) -> List[DiffOpOut]:
    """
    使用 Python difflib SequenceMatcher 计算字符级 diff。
    返回 DiffOpOut 列表。
    """
    from difflib import SequenceMatcher

    ops: List[DiffOpOut] = []
    matcher = SequenceMatcher(None, base, proposed, autojunk=False)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            ops.append(DiffOpOut(type="equal", text=base[i1:i2]))
        elif tag == "insert":
            ops.append(DiffOpOut(type="insert", text=proposed[j1:j2]))
        elif tag == "delete":
            ops.append(DiffOpOut(type="delete", text=base[i1:i2]))
        elif tag == "replace":
            ops.append(DiffOpOut(type="delete", text=base[i1:i2]))
            ops.append(DiffOpOut(type="insert", text=proposed[j1:j2]))
    return ops


# ── 创建 revision ─────────────────────────────────────────────────────────────

def create_revision(
    session: Session,
    segment_id: str,
    proposed_text: str,
    proposer: RevisionProposerEnum,
) -> SegmentRevision:
    seg = session.get(Segment, segment_id)
    if not seg:
        raise AppError(ErrorCode.NOT_FOUND, "Segment not found", 404)
    if seg.pending_revision_id:
        raise AppError(
            ErrorCode.SEGMENT_HAS_PENDING_REVISION,
            "Segment already has a pending revision",
            409,
            {"revisionId": seg.pending_revision_id},
        )

    diff_ops = _compute_diff(seg.current_text, proposed_text)
    rev = SegmentRevision(
        segment_id=segment_id,
        base_text=seg.current_text,
        proposed_text=proposed_text,
        proposer=proposer,
        state=RevisionStateEnum.pending,
        diff_json=json.dumps([op.model_dump() for op in diff_ops], ensure_ascii=False),
    )
    session.add(rev)
    session.flush()

    seg.pending_revision_id = rev.id
    session.add(seg)
    session.commit()
    session.refresh(rev)
    return rev


# ── 应用（accept / reject）────────────────────────────────────────────────────

def apply_revision(
    session: Session,
    revision_id: str,
    action: str,   # "accept" | "reject"
    doc_source_lang: str,
    doc_target_lang: str,
) -> tuple[Segment, SegmentRevision]:
    rev = session.get(SegmentRevision, revision_id)
    if not rev:
        raise AppError(ErrorCode.NOT_FOUND, "Revision not found", 404)
    if rev.state != RevisionStateEnum.pending:
        raise AppError(
            ErrorCode.REVISION_NOT_PENDING,
            "Revision is not in pending state",
            409,
            {"revisionId": revision_id},
        )

    seg = session.get(Segment, rev.segment_id)
    if not seg:
        raise AppError(ErrorCode.NOT_FOUND, "Segment not found", 404)

    if action == "accept":
        rev.state = RevisionStateEnum.accepted
        old_text = seg.current_text
        seg.current_text = rev.proposed_text
        seg.target_status = TargetStatusEnum.accepted
        seg.pending_revision_id = None
        session.add(seg)
        session.add(rev)

        # 写 EditRecord
        record = EditRecord(
            document_id=seg.document_id,
            segment_id=seg.id,
            source_lang=doc_source_lang,
            target_lang=doc_target_lang,
            source_text=seg.source_text,
            base_text=old_text,
            accepted_text=rev.proposed_text,
            proposer=rev.proposer.value,
            extracted=False,
        )
        session.add(record)

    elif action == "reject":
        rev.state = RevisionStateEnum.rejected
        seg.pending_revision_id = None
        session.add(seg)
        session.add(rev)
    else:
        raise AppError(ErrorCode.VALIDATION_ERROR, "action must be accept or reject", 422)

    session.commit()
    session.refresh(seg)
    session.refresh(rev)
    return seg, rev
