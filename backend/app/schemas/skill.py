"""
Pydantic DTOs for Skills（SkillSet / GlossaryEntry / HabitRule / EditRecord）
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ── SkillSet ──────────────────────────────────────────────────────────────────

class SkillSetOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    scope: str
    source_lang: Optional[str] = Field(default=None, alias="sourceLang")
    target_lang: Optional[str] = Field(default=None, alias="targetLang")
    created_at: datetime = Field(alias="createdAt")
    updated_at: datetime = Field(alias="updatedAt")


class CreateSkillSetRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    scope: str  # universal | lang_pair
    source_lang: Optional[str] = Field(default=None, alias="sourceLang")
    target_lang: Optional[str] = Field(default=None, alias="targetLang")


# ── GlossaryEntry ─────────────────────────────────────────────────────────────

class GlossaryEntryOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    skill_set_id: str = Field(alias="skillSetId")
    source_term: str = Field(alias="sourceTerm")
    target_term: str = Field(alias="targetTerm")
    domain: Optional[str] = None
    note: Optional[str] = None
    origin: str
    created_at: datetime = Field(alias="createdAt")


class CreateGlossaryEntryRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    source_term: str = Field(alias="sourceTerm")
    target_term: str = Field(alias="targetTerm")
    domain: Optional[str] = None
    note: Optional[str] = None


# ── HabitRule ─────────────────────────────────────────────────────────────────

class HabitRuleOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    skill_set_id: str = Field(alias="skillSetId")
    description: str
    example: Optional[dict] = None
    origin: str
    confidence: float
    created_at: datetime = Field(alias="createdAt")


class CreateHabitRuleRequest(BaseModel):
    description: str
    example: Optional[dict] = None


# ── EditRecord ────────────────────────────────────────────────────────────────

class EditRecordOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    document_id: str = Field(alias="documentId")
    segment_id: str = Field(alias="segmentId")
    source_lang: str = Field(alias="sourceLang")
    target_lang: str = Field(alias="targetLang")
    source_text: str = Field(alias="sourceText")
    base_text: str = Field(alias="baseText")
    accepted_text: str = Field(alias="acceptedText")
    proposer: str
    created_at: datetime = Field(alias="createdAt")
    extracted: bool


# ── Extraction ────────────────────────────────────────────────────────────────

class ExtractRequest(BaseModel):
    max_records: int = Field(default=50, alias="maxRecords")
    model_config = ConfigDict(populate_by_name=True)


class ExtractResult(BaseModel):
    extracted_count: int = Field(alias="extractedCount")
    added_glossary: int = Field(alias="addedGlossary")
    added_habits: int = Field(alias="addedHabits")
    model_config = ConfigDict(populate_by_name=True)


# ── Full SkillSet detail ──────────────────────────────────────────────────────

class SkillSetDetailOut(BaseModel):
    skill_set: SkillSetOut = Field(alias="skillSet")
    glossary: List[GlossaryEntryOut] = []
    habits: List[HabitRuleOut] = []
    model_config = ConfigDict(populate_by_name=True)
