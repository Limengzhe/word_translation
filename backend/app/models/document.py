"""
数据库模型：Document / Segment / SegmentRevision
"""
import json
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Column
from sqlalchemy import Enum as SAEnum
from sqlalchemy import Text
from sqlmodel import Field, SQLModel


class TargetStatusEnum(str, Enum):
    machine = "machine"
    accepted = "accepted"


class SourceStatusEnum(str, Enum):
    clean = "clean"
    source_edited = "source_edited"
    syncing = "syncing"


class RevisionProposerEnum(str, Enum):
    user = "user"
    model = "model"


class RevisionStateEnum(str, Enum):
    pending = "pending"
    accepted = "accepted"
    rejected = "rejected"


def _new_doc_id() -> str:
    return f"doc_{uuid.uuid4().hex[:12]}"


def _new_seg_id() -> str:
    return f"seg_{uuid.uuid4().hex[:12]}"


def _new_rev_id() -> str:
    return f"rev_{uuid.uuid4().hex[:12]}"


class Document(SQLModel, table=True):
    __tablename__ = "document"

    id: str = Field(default_factory=_new_doc_id, primary_key=True)
    source_lang: str = Field(max_length=16)
    target_lang: str = Field(max_length=16)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    settings_json: str = Field(sa_column=Column(Text, nullable=False, default="{}"))
    # Mammoth 输出的完整 HTML（含表格/标题/列表等原始排版）
    full_source_html: Optional[str] = Field(default=None, sa_column=Column(Text))
    # LLM 翻译后的完整 HTML（结构与 full_source_html 对应）
    full_translated_html: Optional[str] = Field(default=None, sa_column=Column(Text))

    def get_settings(self) -> dict:
        try:
            return json.loads(self.settings_json)
        except Exception:
            return {}


class Segment(SQLModel, table=True):
    __tablename__ = "segment"

    id: str = Field(default_factory=_new_seg_id, primary_key=True)
    document_id: str = Field(foreign_key="document.id", index=True)
    index: int
    # para_type: h1/h2/h3/h4/p/li/blockquote — 保留原文段落结构
    para_type: str = Field(default="p", max_length=16)
    # source_html: Mammoth 生成的原始 HTML 片段（含加粗/斜体/下划线等内联格式）
    source_html: Optional[str] = Field(default=None, sa_column=Column(Text))
    source_text: str = Field(sa_column=Column(Text, nullable=False))
    synced_source_text: str = Field(sa_column=Column(Text, nullable=False, default=""))
    current_text: str = Field(sa_column=Column(Text, nullable=False, default=""))
    target_status: TargetStatusEnum = Field(
        default=TargetStatusEnum.machine,
        sa_column=Column(SAEnum(TargetStatusEnum), nullable=False),
    )
    source_status: SourceStatusEnum = Field(
        default=SourceStatusEnum.clean,
        sa_column=Column(SAEnum(SourceStatusEnum), nullable=False),
    )
    pending_revision_id: Optional[str] = Field(default=None)


class SegmentRevision(SQLModel, table=True):
    __tablename__ = "segmentrevision"

    id: str = Field(default_factory=_new_rev_id, primary_key=True)
    segment_id: str = Field(foreign_key="segment.id", index=True)
    base_text: str = Field(sa_column=Column(Text, nullable=False))
    proposed_text: str = Field(sa_column=Column(Text, nullable=False))
    proposer: RevisionProposerEnum = Field(
        sa_column=Column(SAEnum(RevisionProposerEnum), nullable=False)
    )
    state: RevisionStateEnum = Field(
        default=RevisionStateEnum.pending,
        sa_column=Column(SAEnum(RevisionStateEnum), nullable=False),
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    diff_json: Optional[str] = Field(default=None, sa_column=Column(Text))
