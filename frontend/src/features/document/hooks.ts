import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback, useRef, useState } from 'react'
import * as docApi from '../../lib/api/documents'
import * as segApi from '../../lib/api/segments'
import * as revApi from '../../lib/api/revisions'
import type {
  CreateDocumentRequest,
  SegmentDto,
  SegmentRevisionDto,
} from '../../types/contract'

// ── Document ──────────────────────────────────────────────────────────────────

export function useDocument(docId: string) {
  return useQuery({
    queryKey: ['document', docId],
    queryFn: () => docApi.getDocument(docId),
    enabled: !!docId,
  })
}

export function useCreateDocument() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: CreateDocumentRequest) => docApi.createDocument(body),
    onSuccess: (data) => {
      console.log(`[createDoc] docId=${data.document.id} segments=${data.segments.length}`)
      qc.setQueryData(['document', data.document.id], data)
    },
    onError: (err) => {
      console.error(`[createDoc] error`, err)
    },
  })
}

// ── Translate (SSE) ───────────────────────────────────────────────────────────

export function useTranslateStream(docId: string) {
  const qc = useQueryClient()
  const [isTranslating, setIsTranslating] = useState(false)
  const [progress, setProgress] = useState<{ done: number; total: number }>({ done: 0, total: 0 })
  const abortRef = useRef<boolean>(false)

  const start = useCallback(
    async (stylePreset?: string) => {
      setIsTranslating(true)
      abortRef.current = false
      console.log(`[translate] start docId=${docId}`)
      try {
        for await (const { event, data } of docApi.translateStream(docId, stylePreset)) {
          if (abortRef.current) break

          if (event === 'started') {
            const p = JSON.parse(data)
            console.log(`[translate] started total=${p.total}`)
            setProgress({ done: 0, total: p.total })

          } else if (event === 'segment') {
            // SSE payload: { segmentId, index, currentText, status }
            // Note: "status" maps to targetStatus in SegmentDto
            const payload = JSON.parse(data) as {
              segmentId: string
              index: number
              currentText: string
              status: string
            }
            console.log(`[translate] segment index=${payload.index} text="${payload.currentText.slice(0, 40)}"`)
            qc.setQueryData(['document', docId], (old: any) => {
              if (!old) return old
              const updated = old.segments.map((s: SegmentDto) =>
                s.id === payload.segmentId
                  ? {
                      ...s,
                      currentText: payload.currentText,
                      targetStatus: payload.status,
                    }
                  : s,
              )
              return { ...old, segments: updated }
            })
            setProgress((p) => ({ ...p, done: p.done + 1 }))

          } else if (event === 'error') {
            const e = JSON.parse(data)
            console.warn(`[translate] segment error`, e)

          } else if (event === 'completed') {
            const c = JSON.parse(data)
            console.log(`[translate] completed translated=${c.translated}`)
          }
        }
      } catch (err) {
        console.error(`[translate] stream error`, err)
      } finally {
        setIsTranslating(false)
        console.log(`[translate] done`)
      }
    },
    [docId, qc],
  )

  const stop = useCallback(() => {
    abortRef.current = true
  }, [])

  return { start, stop, isTranslating, progress }
}

// ── Patch Full HTML ───────────────────────────────────────────────────────────

export function usePatchFullHtml(docId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { fullSourceHtml?: string; fullTranslatedHtml?: string }) =>
      docApi.patchFullHtml(docId, body),
    onSuccess: (_, variables) => {
      // 更新本地缓存里的 document 字段
      qc.setQueryData(['document', docId], (old: any) => {
        if (!old) return old
        return {
          ...old,
          document: {
            ...old.document,
            ...(variables.fullSourceHtml !== undefined && { fullSourceHtml: variables.fullSourceHtml }),
            ...(variables.fullTranslatedHtml !== undefined && { fullTranslatedHtml: variables.fullTranslatedHtml }),
          },
        }
      })
    },
  })
}

// ── Translate Full HTML (SSE) ─────────────────────────────────────────────────

/**
 * 流式翻译 hook：token 直接写 DOM，绕过 React 渲染周期以获得最低延迟。
 * 调用方通过 setTargetEl(ref.current) 注册目标 DOM 元素。
 */
export function useTranslateFullStream(docId: string) {
  const qc = useQueryClient()
  const [isTranslating, setIsTranslating] = useState(false)
  const [progressText, setProgressText] = useState('')
  const abortRef = useRef<boolean>(false)
  const collectedRef = useRef('')
  const targetElRef = useRef<HTMLElement | null>(null)
  const rafRef = useRef(0)
  const finalHtmlRef = useRef('')

  const setTargetEl = useCallback((el: HTMLElement | null) => {
    targetElRef.current = el
  }, [])

  const start = useCallback(
    async (stylePreset?: string) => {
      setIsTranslating(true)
      setProgressText('连接翻译服务…')
      collectedRef.current = ''
      finalHtmlRef.current = ''
      abortRef.current = false
      if (targetElRef.current) targetElRef.current.innerHTML = ''
      const t0 = performance.now()
      let firstTokenTime = 0
      let tokenCount = 0
      console.log(`[translateFull] start docId=${docId}`)
      try {
        for await (const { event, data } of docApi.translateFullStream(docId, stylePreset)) {
          if (abortRef.current) break

          if (event === 'started') {
            setProgressText('等待首个 token…')
            console.log(`[translateFull] started`)

          } else if (event === 'token') {
            const tok = JSON.parse(data).token ?? ''
            collectedRef.current += tok
            tokenCount++
            if (tokenCount === 1) {
              firstTokenTime = performance.now() - t0
              console.log(`[translateFull] first token in ${firstTokenTime.toFixed(0)}ms`)
              setProgressText('翻译中…')
            }
            // 直接写 DOM，用 rAF 合并高频更新
            cancelAnimationFrame(rafRef.current)
            rafRef.current = requestAnimationFrame(() => {
              if (targetElRef.current) {
                targetElRef.current.innerHTML = collectedRef.current
              }
            })

          } else if (event === 'completed') {
            cancelAnimationFrame(rafRef.current)
            const c = JSON.parse(data)
            const elapsed = performance.now() - t0
            console.log(
              `[translateFull] completed tokens=${tokenCount} firstToken=${firstTokenTime.toFixed(0)}ms total=${elapsed.toFixed(0)}ms html=${c.translatedHtml?.length ?? 0}`,
            )
            const finalHtml = c.translatedHtml || collectedRef.current
            finalHtmlRef.current = finalHtml
            if (targetElRef.current) targetElRef.current.innerHTML = finalHtml
            qc.setQueryData(['document', docId], (old: any) => {
              if (!old) return old
              return {
                ...old,
                document: { ...old.document, fullTranslatedHtml: finalHtml },
              }
            })
            setProgressText('')

          } else if (event === 'error') {
            cancelAnimationFrame(rafRef.current)
            if (targetElRef.current && collectedRef.current) {
              targetElRef.current.innerHTML = collectedRef.current
            }
            const e = JSON.parse(data)
            console.error(`[translateFull] error`, e)
            setProgressText(`翻译失败：${e.message ?? e.code}`)
          }
        }
      } catch (err) {
        console.error(`[translateFull] stream error`, err)
        cancelAnimationFrame(rafRef.current)
        if (targetElRef.current && collectedRef.current) {
          targetElRef.current.innerHTML = collectedRef.current
        }
        setProgressText('连接中断')
      } finally {
        setIsTranslating(false)
      }
    },
    [docId, qc],
  )

  const stop = useCallback(() => {
    abortRef.current = true
    cancelAnimationFrame(rafRef.current)
  }, [])

  return { start, stop, isTranslating, progressText, setTargetEl, finalHtmlRef }
}

// ── Patch Source ──────────────────────────────────────────────────────────────

export function usePatchSource(docId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ segmentId, sourceText }: { segmentId: string; sourceText: string }) =>
      segApi.patchSource(segmentId, { sourceText }),
    onSuccess: ({ segment }) => {
      qc.setQueryData(['document', docId], (old: any) => {
        if (!old) return old
        return {
          ...old,
          segments: old.segments.map((s: SegmentDto) =>
            s.id === segment.id ? segment : s,
          ),
        }
      })
    },
  })
}

// ── Sync Segment (SSE) ────────────────────────────────────────────────────────

export function useSyncSegment(docId: string) {
  const qc = useQueryClient()
  const [syncingIds, setSyncingIds] = useState<Set<string>>(new Set())

  const sync = useCallback(
    async (segmentId: string) => {
      setSyncingIds((s) => new Set(s).add(segmentId))
      console.log(`[sync] start segmentId=${segmentId}`)
      try {
        let proposed = ''
        for await (const { event, data } of segApi.syncSegmentStream(segmentId)) {
          if (event === 'token') {
            const tok = JSON.parse(data).token ?? ''
            proposed += tok
            qc.setQueryData(['document', docId], (old: any) => {
              if (!old) return old
              return {
                ...old,
                segments: old.segments.map((s: SegmentDto) =>
                  s.id === segmentId
                    ? { ...s, sourceStatus: 'syncing', _streamingText: proposed }
                    : s,
                ),
              }
            })
          } else if (event === 'completed') {
            const c = JSON.parse(data)
            console.log(`[sync] completed proposedText="${c.proposedText?.slice(0, 60)}"`)
          } else if (event === 'revision_created') {
            const { revisionId, proposedText } = JSON.parse(data)
            console.log(`[sync] revision_created revisionId=${revisionId}`)
            qc.setQueryData(['document', docId], (old: any) => {
              if (!old) return old
              return {
                ...old,
                segments: old.segments.map((s: SegmentDto) =>
                  s.id === segmentId
                    ? {
                        ...s,
                        sourceStatus: 'clean',
                        pendingRevisionId: revisionId,
                        _streamingText: undefined,
                      }
                    : s,
                ),
              }
            })
            qc.setQueryData(['revision', revisionId], {
              id: revisionId,
              segmentId,
              proposedText,
              state: 'pending',
            } as Partial<SegmentRevisionDto>)
          }
        }
      } catch (err) {
        console.error(`[sync] error`, err)
      } finally {
        setSyncingIds((s) => {
          const ns = new Set(s)
          ns.delete(segmentId)
          return ns
        })
        console.log(`[sync] done segmentId=${segmentId}`)
      }
    },
    [docId, qc],
  )

  return { sync, syncingIds }
}

// ── Patch Target ──────────────────────────────────────────────────────────────

export function usePatchTarget(docId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ segmentId, text }: { segmentId: string; text: string }) =>
      segApi.patchTarget(segmentId, { userEditedText: text }),
    onSuccess: ({ revision }) => {
      qc.setQueryData(['revision', revision.id], revision)
      qc.setQueryData(['document', docId], (old: any) => {
        if (!old) return old
        return {
          ...old,
          segments: old.segments.map((s: SegmentDto) =>
            s.id === revision.segmentId
              ? { ...s, pendingRevisionId: revision.id }
              : s,
          ),
        }
      })
    },
  })
}

// ── Rewrite ───────────────────────────────────────────────────────────────────

export function useRewrite(docId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ segmentId, instruction }: { segmentId: string; instruction: string }) =>
      segApi.rewriteSegment(segmentId, { instruction }),
    onSuccess: ({ revision }) => {
      qc.setQueryData(['revision', revision.id], revision)
      qc.setQueryData(['document', docId], (old: any) => {
        if (!old) return old
        return {
          ...old,
          segments: old.segments.map((s: SegmentDto) =>
            s.id === revision.segmentId
              ? { ...s, pendingRevisionId: revision.id }
              : s,
          ),
        }
      })
    },
  })
}

// ── Apply Revision ────────────────────────────────────────────────────────────

export function useApplyRevision(docId: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ revisionId, action }: { revisionId: string; action: 'accept' | 'reject' }) =>
      revApi.applyRevision(revisionId, { action }),
    onSuccess: ({ segment, revision }) => {
      qc.setQueryData(['document', docId], (old: any) => {
        if (!old) return old
        return {
          ...old,
          segments: old.segments.map((s: SegmentDto) =>
            s.id === segment.id ? segment : s,
          ),
        }
      })
      qc.setQueryData(['revision', revision.id], revision)
    },
  })
}

// ── Revision detail ───────────────────────────────────────────────────────────

export function useRevision(revisionId: string | undefined) {
  return useQuery({
    queryKey: ['revision', revisionId],
    queryFn: async () => {
      // Revision 数据由各 mutation onSuccess 写入缓存，无专用 GET 接口
      return null as SegmentRevisionDto | null
    },
    enabled: false, // 只从缓存读取
  })
}
