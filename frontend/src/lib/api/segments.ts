import { apiFetch, fetchSSE } from './client'
import type {
  PatchSourceRequest,
  PatchTargetRequest,
  RewriteRequest,
  SegmentRevisionDto,
  SegmentDto,
} from '../../types/contract'

export function patchSource(segmentId: string, body: PatchSourceRequest) {
  return apiFetch<{ segment: SegmentDto }>(`/segments/${segmentId}/source`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  })
}

export async function* syncSegmentStream(segmentId: string) {
  yield* fetchSSE(`/segments/${segmentId}/sync`, { method: 'POST' })
}

export function rewriteSegment(segmentId: string, body: RewriteRequest) {
  return apiFetch<{ revision: SegmentRevisionDto }>(`/segments/${segmentId}/rewrite`, {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function patchTarget(segmentId: string, body: PatchTargetRequest) {
  return apiFetch<{ revision: SegmentRevisionDto }>(`/segments/${segmentId}/target`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  })
}
