"""
Pydantic DTOs for Documents / Segments / Revisions
所有字段名与前端 contract.ts 保持一致（camelCase via alias）
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


# ── Settings ────────────────────────────────────────────────────────────────

class DocumentSettings(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    provider: str = Field(default="openai", alias="provider")
    model: str = Field(default="gpt-4.1-mini", alias="model")
    temperature: float = Field(default=0.2, alias="temperature")
    style_preset: Optional[str] = Field(default=None, alias="stylePreset")
    glossary_id: Optional[str] = Field(default=None, alias="glossaryId")


# ── Document ─────────────────────────────────────────────────────────────────

class DocumentOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    source_lang: str = Field(alias="sourceLang")
    target_lang: str = Field(alias="targetLang")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")
    settings: DocumentSettings
    full_source_html: Optional[str] = Field(default=None, alias="fullSourceHtml")
    full_translated_html: Optional[str] = Field(default=None, alias="fullTranslatedHtml")


class ParagraphIn(BaseModel):
    """单个段落（来自前端 Mammoth 解析结果）"""
    model_config = ConfigDict(populate_by_name=True)

    text: str
    para_type: str = Field(default="p", alias="paraType")
    source_html: Optional[str] = Field(default=None, alias="sourceHtml")


class CreateDocumentRequest(BaseModel):
    source_lang: str = Field(alias="sourceLang")
    target_lang: str = Field(alias="targetLang")
    # paragraphs 优先；source_text 作为纯文本 fallback
    paragraphs: Optional[List[ParagraphIn]] = Field(default=None)
    source_text: Optional[str] = Field(default=None, alias="sourceText")
    # Mammoth 输出的完整 HTML（包含表格/标题等原始排版）
    full_source_html: Optional[str] = Field(default=None, alias="fullSourceHtml")
    settings: DocumentSettings = Field(default_factory=DocumentSettings)

    model_config = ConfigDict(populate_by_name=True)


# ── Segment ───────────────────────────────────────────────────────────────────

class SegmentOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    document_id: str = Field(alias="documentId")
    index: int
    para_type: str = Field(default="p", alias="paraType")
    source_html: Optional[str] = Field(default=None, alias="sourceHtml")
    source_text: str = Field(alias="sourceText")
    synced_source_text: str = Field(alias="syncedSourceText")
    current_text: str = Field(alias="currentText")
    target_status: str = Field(alias="targetStatus")
    source_status: str = Field(alias="sourceStatus")
    pending_revision_id: Optional[str] = Field(default=None, alias="pendingRevisionId")


# ── DiffOp ────────────────────────────────────────────────────────────────────

class DiffOpOut(BaseModel):
    type: str   # equal | insert | delete
    text: str


# ── Revision ──────────────────────────────────────────────────────────────────

class RevisionOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    segment_id: str = Field(alias="segmentId")
    base_text: str = Field(alias="baseText")
    proposed_text: str = Field(alias="proposedText")
    proposer: str
    state: str
    created_at: datetime = Field(alias="createdAt")
    diff: Optional[List[DiffOpOut]] = None


# ── Requests ──────────────────────────────────────────────────────────────────

class PatchSourceRequest(BaseModel):
    source_text: str = Field(alias="sourceText")
    model_config = ConfigDict(populate_by_name=True)


class PatchTargetRequest(BaseModel):
    user_edited_text: str = Field(alias="userEditedText")
    model_config = ConfigDict(populate_by_name=True)


class RewriteRequest(BaseModel):
    instruction: str
    style_preset: Optional[str] = Field(default=None, alias="stylePreset")
    model_config = ConfigDict(populate_by_name=True)


class ApplyRevisionRequest(BaseModel):
    action: str  # accept | reject


class TranslateStreamRequest(BaseModel):
    style_preset: Optional[str] = Field(default=None, alias="stylePreset")
    model_config = ConfigDict(populate_by_name=True)


class PatchFullHtmlRequest(BaseModel):
    """PATCH /documents/{id}/full-html：保存编辑后的 HTML。"""
    model_config = ConfigDict(populate_by_name=True)

    full_source_html: Optional[str] = Field(default=None, alias="fullSourceHtml")
    full_translated_html: Optional[str] = Field(default=None, alias="fullTranslatedHtml")


# ── Composite responses ───────────────────────────────────────────────────────

class CreateDocumentResponse(BaseModel):
    document: DocumentOut
    segments: List[SegmentOut]


class GetDocumentResponse(BaseModel):
    document: DocumentOut
    segments: List[SegmentOut]


class PatchSegmentSourceResponse(BaseModel):
    segment: SegmentOut


class PatchSegmentTargetResponse(BaseModel):
    revision: RevisionOut


class RewriteResponse(BaseModel):
    revision: RevisionOut


class ApplyRevisionResponse(BaseModel):
    segment: SegmentOut
    revision: RevisionOut
