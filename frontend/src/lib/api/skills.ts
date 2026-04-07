import { apiFetch } from './client'
import type {
  EditRecordDto,
  ExtractResult,
  GlossaryEntryDto,
  HabitRuleDto,
  SkillSetDetailDto,
  SkillSetDto,
} from '../../types/contract'

export function listSkillSets() {
  return apiFetch<SkillSetDto[]>('/skillsets')
}

export function createSkillSet(body: {
  name: string
  scope: string
  sourceLang?: string
  targetLang?: string
}) {
  return apiFetch<SkillSetDto>('/skillsets', { method: 'POST', body: JSON.stringify(body) })
}

export function getSkillSet(id: string) {
  return apiFetch<SkillSetDetailDto>(`/skillsets/${id}`)
}

export function addGlossaryEntry(
  skillSetId: string,
  body: { sourceTerm: string; targetTerm: string; domain?: string; note?: string },
) {
  return apiFetch<GlossaryEntryDto>(`/skillsets/${skillSetId}/glossary`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function deleteGlossaryEntry(skillSetId: string, entryId: string) {
  return apiFetch<void>(`/skillsets/${skillSetId}/glossary/${entryId}`, { method: 'DELETE' })
}

export function addHabitRule(
  skillSetId: string,
  body: { description: string; example?: object },
) {
  return apiFetch<HabitRuleDto>(`/skillsets/${skillSetId}/habits`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function deleteHabitRule(skillSetId: string, habitId: string) {
  return apiFetch<void>(`/skillsets/${skillSetId}/habits/${habitId}`, { method: 'DELETE' })
}

export function extractSkills(skillSetId: string, maxRecords = 50) {
  return apiFetch<ExtractResult>(`/skillsets/${skillSetId}/extract`, {
    method: 'POST',
    body: JSON.stringify({ maxRecords }),
  })
}

export function listEditRecords(skillSetId: string, page = 1) {
  return apiFetch<EditRecordDto[]>(
    `/skillsets/${skillSetId}/edit-records?page=${page}&page_size=50`,
  )
}
