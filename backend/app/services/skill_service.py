"""
Skill 服务：CRUD + LLM 提炼 EditRecord → GlossaryEntry / HabitRule。
"""
import json
from datetime import datetime
from typing import List

from sqlmodel import Session, select

from app.core.errors import AppError, ErrorCode
from app.models.skill import (
    EditRecord,
    GlossaryEntry,
    HabitRule,
    OriginEnum,
    SkillScopeEnum,
    SkillSet,
)
from app.providers.base import TranslatorProvider


# ── SkillSet CRUD ─────────────────────────────────────────────────────────────

def create_skill_set(
    session: Session,
    name: str,
    scope: str,
    source_lang: str | None,
    target_lang: str | None,
) -> SkillSet:
    ss = SkillSet(
        name=name,
        scope=SkillScopeEnum(scope),
        source_lang=source_lang,
        target_lang=target_lang,
    )
    session.add(ss)
    session.commit()
    session.refresh(ss)
    return ss


def list_skill_sets(session: Session) -> List[SkillSet]:
    return session.exec(select(SkillSet)).all()


def get_skill_set(session: Session, skill_set_id: str) -> SkillSet:
    ss = session.get(SkillSet, skill_set_id)
    if not ss:
        raise AppError(ErrorCode.NOT_FOUND, "SkillSet not found", 404)
    return ss


# ── Glossary CRUD ─────────────────────────────────────────────────────────────

def add_glossary_entry(
    session: Session,
    skill_set_id: str,
    source_term: str,
    target_term: str,
    domain: str | None = None,
    note: str | None = None,
    origin: OriginEnum = OriginEnum.manual,
) -> GlossaryEntry:
    get_skill_set(session, skill_set_id)
    entry = GlossaryEntry(
        skill_set_id=skill_set_id,
        source_term=source_term,
        target_term=target_term,
        domain=domain,
        note=note,
        origin=origin,
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


def delete_glossary_entry(session: Session, skill_set_id: str, entry_id: str) -> None:
    entry = session.get(GlossaryEntry, entry_id)
    if not entry or entry.skill_set_id != skill_set_id:
        raise AppError(ErrorCode.NOT_FOUND, "GlossaryEntry not found", 404)
    session.delete(entry)
    session.commit()


# ── HabitRule CRUD ────────────────────────────────────────────────────────────

def add_habit_rule(
    session: Session,
    skill_set_id: str,
    description: str,
    example: dict | None = None,
    origin: OriginEnum = OriginEnum.manual,
    confidence: float = 1.0,
) -> HabitRule:
    get_skill_set(session, skill_set_id)
    habit = HabitRule(
        skill_set_id=skill_set_id,
        description=description,
        example_json=json.dumps(example, ensure_ascii=False) if example else None,
        origin=origin,
        confidence=confidence,
    )
    session.add(habit)
    session.commit()
    session.refresh(habit)
    return habit


def delete_habit_rule(session: Session, skill_set_id: str, habit_id: str) -> None:
    habit = session.get(HabitRule, habit_id)
    if not habit or habit.skill_set_id != skill_set_id:
        raise AppError(ErrorCode.NOT_FOUND, "HabitRule not found", 404)
    session.delete(habit)
    session.commit()


# ── 提炼 ──────────────────────────────────────────────────────────────────────

_EXTRACT_PROMPT = """\
下面是一组翻译操作记录，每条包含：原文、AI 初始译文（修改前）、人工接受的译文（修改后）。
请分析这些修改，提炼出：
1. 词表（glossary）：source_term → target_term 的固定对应关系（若有）
2. 翻译习惯（habits）：体现的翻译风格、措辞偏好、句式习惯等规律

请以 JSON 格式返回（不要其他内容）：
{{
  "glossary": [
    {{"source_term": "...", "target_term": "...", "domain": "tech|medical|general|null"}}
  ],
  "habits": [
    {{"description": "...", "example": {{"source": "...", "preferred": "...", "avoided": "..."}}}}
  ]
}}

操作记录：
{records}"""


async def extract_from_edit_records(
    session: Session,
    skill_set_id: str,
    provider: TranslatorProvider,
    max_records: int = 50,
) -> dict:
    ss = get_skill_set(session, skill_set_id)

    # 取未提炼记录（语种对匹配）
    query = select(EditRecord).where(EditRecord.extracted == False)
    if ss.scope == SkillScopeEnum.lang_pair and ss.source_lang and ss.target_lang:
        query = query.where(
            EditRecord.source_lang == ss.source_lang,
            EditRecord.target_lang == ss.target_lang,
        )
    query = query.limit(max_records)
    records: List[EditRecord] = session.exec(query).all()

    if not records:
        return {"extractedCount": 0, "addedGlossary": 0, "addedHabits": 0}

    record_lines = []
    for i, r in enumerate(records, 1):
        record_lines.append(
            f"[{i}]\n原文: {r.source_text}\n修改前: {r.base_text}\n接受版本: {r.accepted_text}"
        )

    prompt_text = _EXTRACT_PROMPT.format(records="\n\n".join(record_lines))

    # 调用模型（非流式）
    result_text = await provider.translate_once(
        source_text=prompt_text,
        source_lang="zh",
        target_lang="zh",
        system_prompt="你是翻译质量分析专家。请严格按 JSON 格式输出，不要任何额外说明。",
    )

    added_glossary = 0
    added_habits = 0
    try:
        # 提取 JSON（模型可能包裹在 ```json ... ``` 中）
        text = result_text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        parsed = json.loads(text)

        existing_terms = {
            e.source_term.lower()
            for e in session.exec(
                select(GlossaryEntry).where(GlossaryEntry.skill_set_id == skill_set_id)
            ).all()
        }

        for item in parsed.get("glossary", []):
            if item.get("source_term", "").lower() not in existing_terms:
                add_glossary_entry(
                    session,
                    skill_set_id,
                    item["source_term"],
                    item["target_term"],
                    domain=item.get("domain") or None,
                    origin=OriginEnum.extracted,
                )
                existing_terms.add(item["source_term"].lower())
                added_glossary += 1

        for item in parsed.get("habits", []):
            add_habit_rule(
                session,
                skill_set_id,
                item["description"],
                example=item.get("example"),
                origin=OriginEnum.extracted,
                confidence=0.8,
            )
            added_habits += 1

    except Exception:
        pass  # 解析失败不影响记录标记

    # 标记已提炼
    for r in records:
        r.extracted = True
        session.add(r)

    ss.updated_at = datetime.utcnow()
    session.add(ss)
    session.commit()

    return {
        "extractedCount": len(records),
        "addedGlossary": added_glossary,
        "addedHabits": added_habits,
    }
