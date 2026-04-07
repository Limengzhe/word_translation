"""
路由：Skills
GET    /api/skillsets
POST   /api/skillsets
GET    /api/skillsets/{skillSetId}
POST   /api/skillsets/{skillSetId}/glossary
DELETE /api/skillsets/{skillSetId}/glossary/{entryId}
POST   /api/skillsets/{skillSetId}/habits
DELETE /api/skillsets/{skillSetId}/habits/{habitId}
POST   /api/skillsets/{skillSetId}/extract
GET    /api/skillsets/{skillSetId}/edit-records
"""
import json
from typing import List

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.db.session import get_session
from app.models.skill import EditRecord, GlossaryEntry, HabitRule
from app.providers import get_provider
from app.schemas.skill import (
    CreateGlossaryEntryRequest,
    CreateHabitRuleRequest,
    CreateSkillSetRequest,
    EditRecordOut,
    ExtractRequest,
    ExtractResult,
    GlossaryEntryOut,
    HabitRuleOut,
    SkillSetDetailOut,
    SkillSetOut,
)
from app.services.skill_service import (
    add_glossary_entry,
    add_habit_rule,
    create_skill_set,
    delete_glossary_entry,
    delete_habit_rule,
    extract_from_edit_records,
    list_skill_sets,
    get_skill_set,
)

router = APIRouter(prefix="/api/skillsets", tags=["skills"])


def _ss_to_out(ss) -> SkillSetOut:
    return SkillSetOut(
        id=ss.id,
        name=ss.name,
        scope=ss.scope.value,
        sourceLang=ss.source_lang,
        targetLang=ss.target_lang,
        createdAt=ss.created_at,
        updatedAt=ss.updated_at,
    )


def _entry_to_out(e) -> GlossaryEntryOut:
    return GlossaryEntryOut(
        id=e.id,
        skillSetId=e.skill_set_id,
        sourceTerm=e.source_term,
        targetTerm=e.target_term,
        domain=e.domain,
        note=e.note,
        origin=e.origin.value,
        createdAt=e.created_at,
    )


def _habit_to_out(h) -> HabitRuleOut:
    example = None
    if h.example_json:
        try:
            example = json.loads(h.example_json)
        except Exception:
            pass
    return HabitRuleOut(
        id=h.id,
        skillSetId=h.skill_set_id,
        description=h.description,
        example=example,
        origin=h.origin.value,
        confidence=h.confidence,
        createdAt=h.created_at,
    )


@router.get("", response_model=List[SkillSetOut])
def list_sets(session: Session = Depends(get_session)):
    return [_ss_to_out(ss) for ss in list_skill_sets(session)]


@router.post("", response_model=SkillSetOut)
def create_set(body: CreateSkillSetRequest, session: Session = Depends(get_session)):
    ss = create_skill_set(session, body.name, body.scope, body.source_lang, body.target_lang)
    return _ss_to_out(ss)


@router.get("/{skill_set_id}", response_model=SkillSetDetailOut)
def get_set_detail(skill_set_id: str, session: Session = Depends(get_session)):
    ss = get_skill_set(session, skill_set_id)
    entries = session.exec(
        select(GlossaryEntry).where(GlossaryEntry.skill_set_id == skill_set_id)
    ).all()
    habits = session.exec(
        select(HabitRule).where(HabitRule.skill_set_id == skill_set_id)
    ).all()
    return SkillSetDetailOut(
        skillSet=_ss_to_out(ss),
        glossary=[_entry_to_out(e) for e in entries],
        habits=[_habit_to_out(h) for h in habits],
    )


@router.post("/{skill_set_id}/glossary", response_model=GlossaryEntryOut)
def create_entry(
    skill_set_id: str,
    body: CreateGlossaryEntryRequest,
    session: Session = Depends(get_session),
):
    entry = add_glossary_entry(
        session, skill_set_id, body.source_term, body.target_term, body.domain, body.note
    )
    return _entry_to_out(entry)


@router.delete("/{skill_set_id}/glossary/{entry_id}", status_code=204)
def remove_entry(
    skill_set_id: str, entry_id: str, session: Session = Depends(get_session)
):
    delete_glossary_entry(session, skill_set_id, entry_id)


@router.post("/{skill_set_id}/habits", response_model=HabitRuleOut)
def create_habit(
    skill_set_id: str,
    body: CreateHabitRuleRequest,
    session: Session = Depends(get_session),
):
    habit = add_habit_rule(session, skill_set_id, body.description, body.example)
    return _habit_to_out(habit)


@router.delete("/{skill_set_id}/habits/{habit_id}", status_code=204)
def remove_habit(
    skill_set_id: str, habit_id: str, session: Session = Depends(get_session)
):
    delete_habit_rule(session, skill_set_id, habit_id)


@router.post("/{skill_set_id}/extract", response_model=ExtractResult)
async def extract(
    skill_set_id: str,
    body: ExtractRequest = None,
    session: Session = Depends(get_session),
):
    provider = get_provider()
    max_r = body.max_records if body else 50
    result = await extract_from_edit_records(session, skill_set_id, provider, max_r)
    return ExtractResult(
        extractedCount=result["extractedCount"],
        addedGlossary=result["addedGlossary"],
        addedHabits=result["addedHabits"],
    )


@router.get("/{skill_set_id}/edit-records", response_model=List[EditRecordOut])
def list_edit_records(
    skill_set_id: str,
    page: int = 1,
    page_size: int = 50,
    session: Session = Depends(get_session),
):
    ss = get_skill_set(session, skill_set_id)
    query = select(EditRecord)
    if ss.source_lang and ss.target_lang:
        query = query.where(
            EditRecord.source_lang == ss.source_lang,
            EditRecord.target_lang == ss.target_lang,
        )
    query = query.offset((page - 1) * page_size).limit(page_size)
    records = session.exec(query).all()
    return [
        EditRecordOut(
            id=r.id,
            documentId=r.document_id,
            segmentId=r.segment_id,
            sourceLang=r.source_lang,
            targetLang=r.target_lang,
            sourceText=r.source_text,
            baseText=r.base_text,
            acceptedText=r.accepted_text,
            proposer=r.proposer,
            createdAt=r.created_at,
            extracted=r.extracted,
        )
        for r in records
    ]
