import { apiFetch } from './client'
import type { ApplyRevisionRequest, ApplyRevisionResponse } from '../../types/contract'

export function applyRevision(revisionId: string, body: ApplyRevisionRequest) {
  return apiFetch<ApplyRevisionResponse>(`/revisions/${revisionId}`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  })
}
