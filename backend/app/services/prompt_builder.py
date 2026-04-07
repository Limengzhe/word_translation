"""
PromptBuilder：翻译前加载 Skills 并构建 system prompt 额外片段。
"""
from typing import List

from sqlmodel import Session, select

from app.models.skill import GlossaryEntry, HabitRule, SkillScopeEnum, SkillSet


def build_skill_prompt(
    session: Session,
    source_lang: str,
    target_lang: str,
    style_preset: str | None = None,
) -> str:
    """
    加载通用 SkillSet + 语种对 SkillSet，合并词表与习惯规则，
    返回注入 system prompt 的额外文本片段。
    """
    parts: List[str] = []

    # 收集适用的 skill_set id
    skill_set_ids: List[str] = []

    # 1. 通用 SkillSet
    universal_sets = session.exec(
        select(SkillSet).where(SkillSet.scope == SkillScopeEnum.universal)
    ).all()
    skill_set_ids.extend(ss.id for ss in universal_sets)

    # 2. 语种对 SkillSet
    pair_sets = session.exec(
        select(SkillSet).where(
            SkillSet.scope == SkillScopeEnum.lang_pair,
            SkillSet.source_lang == source_lang,
            SkillSet.target_lang == target_lang,
        )
    ).all()
    skill_set_ids.extend(ss.id for ss in pair_sets)

    if not skill_set_ids:
        return ""

    # 3. 词表（去重，语种对优先）
    seen_source_terms: set[str] = set()
    glossary_lines: List[str] = []

    # 先加语种对，再加通用（通过 skill_set_ids 顺序控制）
    pair_ids = [ss.id for ss in pair_sets]
    univ_ids = [ss.id for ss in universal_sets]
    ordered_ids = pair_ids + univ_ids

    for ssid in ordered_ids:
        entries = session.exec(
            select(GlossaryEntry).where(GlossaryEntry.skill_set_id == ssid)
        ).all()
        for e in entries:
            key = e.source_term.lower()
            if key not in seen_source_terms:
                seen_source_terms.add(key)
                glossary_lines.append(f"- {e.source_term} → {e.target_term}")

    if glossary_lines:
        parts.append(
            "【术语表】请严格遵守以下词汇对应关系：\n" + "\n".join(glossary_lines)
        )

    # 4. 习惯规则（按 confidence 降序，取前 20 条）
    all_habits: List[HabitRule] = []
    for ssid in ordered_ids:
        habits = session.exec(
            select(HabitRule).where(HabitRule.skill_set_id == ssid)
        ).all()
        all_habits.extend(habits)

    all_habits.sort(key=lambda h: h.confidence, reverse=True)
    habit_lines = [f"- {h.description}" for h in all_habits[:20]]

    if habit_lines:
        parts.append("【翻译习惯】\n" + "\n".join(habit_lines))

    # 5. 风格预设
    if style_preset:
        style_map = {
            "tech_doc": "技术文档风格：准确、简洁，保留专有名词原文。",
            "formal": "正式书面语风格。",
            "casual": "口语化、自然流畅风格。",
        }
        desc = style_map.get(style_preset, style_preset)
        parts.append(f"【风格要求】{desc}")

    return "\n\n".join(parts)
