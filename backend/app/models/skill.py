"""
Skills 数据库模型：SkillSet / GlossaryEntry / HabitRule / EditRecord
"""
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Boolean, Column
from sqlalchemy import Enum as SAEnum
from sqlalchemy import Float, Text
from sqlmodel import Field, SQLModel


class SkillScopeEnum(str, Enum):
    universal = "universal"
    lang_pair = "lang_pair"


class OriginEnum(str, Enum):
    manual = "manual"
    extracted = "extracted"


def _new_skill_id() -> str:
    return f"sk_{uuid.uuid4().hex[:12]}"


def _new_entry_id() -> str:
    return f"ge_{uuid.uuid4().hex[:12]}"


def _new_habit_id() -> str:
    return f"hr_{uuid.uuid4().hex[:12]}"


def _new_record_id() -> str:
    return f"er_{uuid.uuid4().hex[:12]}"


class SkillSet(SQLModel, table=True):
    __tablename__ = "skillset"

    id: str = Field(default_factory=_new_skill_id, primary_key=True)
    name: str = Field(max_length=128)
    scope: SkillScopeEnum = Field(
        sa_column=Column(SAEnum(SkillScopeEnum), nullable=False)
    )
    source_lang: Optional[str] = Field(default=None, max_length=16)
    target_lang: Optional[str] = Field(default=None, max_length=16)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class GlossaryEntry(SQLModel, table=True):
    __tablename__ = "glossaryentry"

    id: str = Field(default_factory=_new_entry_id, primary_key=True)
    skill_set_id: str = Field(foreign_key="skillset.id", index=True)
    source_term: str = Field(sa_column=Column(Text, nullable=False))
    target_term: str = Field(sa_column=Column(Text, nullable=False))
    domain: Optional[str] = Field(default=None, max_length=64)
    note: Optional[str] = Field(default=None, sa_column=Column(Text))
    origin: OriginEnum = Field(
        default=OriginEnum.manual,
        sa_column=Column(SAEnum(OriginEnum), nullable=False),
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)


class HabitRule(SQLModel, table=True):
    __tablename__ = "habitrule"

    id: str = Field(default_factory=_new_habit_id, primary_key=True)
    skill_set_id: str = Field(foreign_key="skillset.id", index=True)
    description: str = Field(sa_column=Column(Text, nullable=False))
    example_json: Optional[str] = Field(default=None, sa_column=Column(Text))
    origin: OriginEnum = Field(
        default=OriginEnum.manual,
        sa_column=Column(SAEnum(OriginEnum), nullable=False),
    )
    confidence: float = Field(default=1.0, sa_column=Column(Float, nullable=False))
    created_at: datetime = Field(default_factory=datetime.utcnow)


class EditRecord(SQLModel, table=True):
    __tablename__ = "editrecord"

    id: str = Field(default_factory=_new_record_id, primary_key=True)
    document_id: str = Field(index=True)
    segment_id: str = Field(index=True)
    source_lang: str = Field(max_length=16)
    target_lang: str = Field(max_length=16)
    source_text: str = Field(sa_column=Column(Text, nullable=False))
    base_text: str = Field(sa_column=Column(Text, nullable=False))
    accepted_text: str = Field(sa_column=Column(Text, nullable=False))
    proposer: str = Field(max_length=16)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    extracted: bool = Field(default=False, sa_column=Column(Boolean, nullable=False))
