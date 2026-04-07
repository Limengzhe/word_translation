import { apiFetch, fetchSSE } from './client'
import type {
  CreateDocumentRequest,
  CreateDocumentResponse,
  GetDocumentResponse,
} from '../../types/contract'

export function createDocument(body: CreateDocumentRequest) {
  return apiFetch<CreateDocumentResponse>('/documents', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

export function getDocument(docId: string) {
  return apiFetch<GetDocumentResponse>(`/documents/${docId}`)
}

export async function* translateStream(
  docId: string,
  stylePreset?: string,
) {
  yield* fetchSSE(`/documents/${docId}/translate/stream`, {
    method: 'POST',
    body: JSON.stringify({ stylePreset }),
    headers: { 'Content-Type': 'application/json' },
  })
}

/** 全文 HTML 翻译（一次 LLM 调用，流式 token） */
export async function* translateFullStream(
  docId: string,
  stylePreset?: string,
) {
  yield* fetchSSE(`/documents/${docId}/translate-full/stream`, {
    method: 'POST',
    body: JSON.stringify({ stylePreset }),
    headers: { 'Content-Type': 'application/json' },
  })
}

/** 保存编辑后的 HTML */
export function patchFullHtml(
  docId: string,
  body: { fullSourceHtml?: string; fullTranslatedHtml?: string },
) {
  return apiFetch<{ id: string }>(`/documents/${docId}/full-html`, {
    method: 'PATCH',
    body: JSON.stringify(body),
  })
}
