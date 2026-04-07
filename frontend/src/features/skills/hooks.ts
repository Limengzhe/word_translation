import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import * as skillApi from '../../lib/api/skills'

export function useSkillSets() {
  return useQuery({
    queryKey: ['skillsets'],
    queryFn: skillApi.listSkillSets,
  })
}

export function useSkillSet(skillSetId: string | undefined) {
  return useQuery({
    queryKey: ['skillset', skillSetId],
    queryFn: () => skillApi.getSkillSet(skillSetId!),
    enabled: !!skillSetId,
  })
}

export function useCreateSkillSet() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: skillApi.createSkillSet,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['skillsets'] }),
  })
}

export function useAddGlossaryEntry(skillSetId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { sourceTerm: string; targetTerm: string; domain?: string }) =>
      skillApi.addGlossaryEntry(skillSetId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['skillset', skillSetId] }),
  })
}

export function useDeleteGlossaryEntry(skillSetId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (entryId: string) => skillApi.deleteGlossaryEntry(skillSetId, entryId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['skillset', skillSetId] }),
  })
}

export function useAddHabitRule(skillSetId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { description: string }) =>
      skillApi.addHabitRule(skillSetId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['skillset', skillSetId] }),
  })
}

export function useDeleteHabitRule(skillSetId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (habitId: string) => skillApi.deleteHabitRule(skillSetId, habitId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['skillset', skillSetId] }),
  })
}

export function useExtract(skillSetId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (maxRecords?: number) => skillApi.extractSkills(skillSetId, maxRecords),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['skillset', skillSetId] }),
  })
}

export function useEditRecords(skillSetId: string) {
  return useQuery({
    queryKey: ['edit-records', skillSetId],
    queryFn: () => skillApi.listEditRecords(skillSetId),
    enabled: !!skillSetId,
  })
}
