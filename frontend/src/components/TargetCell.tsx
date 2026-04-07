/**
 * TargetCell：译文单元格，按 paraType 渲染段落样式。
 * - 流式状态：显示动态占位
 * - pending revision：显示 DiffView
 * - 普通：显示 currentText
 */
import { useEffect, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import ParaBlock from './ParaBlock'
import DiffView from './DiffView'
import type { DiffOp, SegmentDto, SegmentRevisionDto } from '../types/contract'
import { computeDiff } from '../lib/diff'

interface HighlightRange { start: number; end: number; strong: boolean }

interface Props {
  segment: SegmentDto & { _streamingText?: string }
  docId: string
  highlight?: HighlightRange
  onSaveEdit: (text: string) => void
}

export default function TargetCell({ segment, docId: _docId, highlight, onSaveEdit }: Props) {
  const qc = useQueryClient()
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(segment.currentText)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => { setDraft(segment.currentText) }, [segment.currentText])
  useEffect(() => { if (editing) textareaRef.current?.focus() }, [editing])

  const pendingRev = segment.pendingRevisionId
    ? (qc.getQueryData(['revision', segment.pendingRevisionId]) as SegmentRevisionDto | null)
    : null

  function handleBlur() {
    setEditing(false)
    if (draft.trim() !== segment.currentText) onSaveEdit(draft.trim())
  }

  // ── 流式占位 ──────────────────────────────────────────────────────────────
  if (segment._streamingText !== undefined) {
    return (
      <ParaBlock paraType={segment.paraType}
        className="text-gray-400 italic animate-pulse whitespace-pre-wrap">
        {segment._streamingText || '翻译中…'}
      </ParaBlock>
    )
  }

  // ── 编辑态 ────────────────────────────────────────────────────────────────
  if (editing) {
    return (
      <textarea
        ref={textareaRef}
        className="w-full min-h-[2.5rem] resize-none outline-none text-sm leading-relaxed p-1 bg-white border border-indigo-300 rounded"
        value={draft}
        onChange={e => setDraft(e.target.value)}
        onBlur={handleBlur}
        onKeyDown={e => {
          if (e.key === 'Escape') { setDraft(segment.currentText); setEditing(false) }
        }}
      />
    )
  }

  // ── Diff 视图（pending revision） ─────────────────────────────────────────
  if (pendingRev) {
    const ops: DiffOp[] = pendingRev.diff ?? computeDiff(pendingRev.baseText, pendingRev.proposedText)
    return (
      <ParaBlock
        paraType={segment.paraType}
        data-segment-id={segment.id}
        data-side="target"
        className="select-text whitespace-pre-wrap"
        onDoubleClick={() => setEditing(true)}
      >
        <DiffView ops={ops} />
      </ParaBlock>
    )
  }

  // ── 空状态 ────────────────────────────────────────────────────────────────
  if (!segment.currentText) {
    return (
      <ParaBlock paraType={segment.paraType}
        className="text-gray-300 italic select-none">
        未翻译
      </ParaBlock>
    )
  }

  // ── 普通文本（可选高亮） ──────────────────────────────────────────────────
  const text = segment.currentText
  let content: React.ReactNode

  if (highlight) {
    const { start, end } = highlight
    content = (
      <>
        {text.slice(0, start)}
        <mark className="bg-yellow-200 rounded px-0.5 not-italic">{text.slice(start, end)}</mark>
        {text.slice(end)}
      </>
    )
  } else {
    content = text
  }

  return (
    <ParaBlock
      paraType={segment.paraType}
      data-segment-id={segment.id}
      data-side="target"
      className="select-text whitespace-pre-wrap"
      onDoubleClick={() => setEditing(true)}
    >
      {content}
    </ParaBlock>
  )
}
