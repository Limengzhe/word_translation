/**
 * SourceCell：原文单元格
 * - 有 sourceHtml 时用 dangerouslySetInnerHTML 渲染，保留 Word 内联格式
 * - 双击进入纯文本编辑模式
 * - 支持划选高亮
 */
import { useEffect, useRef, useState } from 'react'
import ParaBlock from './ParaBlock'
import type { SegmentDto } from '../types/contract'

interface HighlightRange { start: number; end: number; strong: boolean }
interface Props {
  segment: SegmentDto
  highlight?: HighlightRange
  onSave: (text: string) => void
}

export default function SourceCell({ segment, highlight, onSave }: Props) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(segment.sourceText)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => { setDraft(segment.sourceText) }, [segment.sourceText])
  useEffect(() => { if (editing) textareaRef.current?.focus() }, [editing])

  function handleBlur() {
    setEditing(false)
    if (draft.trim() !== segment.sourceText) onSave(draft.trim())
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
          if (e.key === 'Escape') { setDraft(segment.sourceText); setEditing(false) }
        }}
      />
    )
  }

  // ── 有 sourceHtml：保留 Word 原始格式渲染 ─────────────────────────────────
  if (segment.sourceHtml) {
    // 若有高亮范围，在纯文本层面标记（简化：整行强高亮时加背景）
    const wrapClass = highlight?.strong ? 'bg-blue-50 rounded' : ''
    return (
      <ParaBlock
        paraType={segment.paraType}
        data-segment-id={segment.id}
        data-side="source"
        className={`cursor-text select-text word-format ${wrapClass}`}
        onDoubleClick={() => setEditing(true)}
      >
        {/* eslint-disable-next-line react/no-danger */}
        <span dangerouslySetInnerHTML={{ __html: segment.sourceHtml }} />
      </ParaBlock>
    )
  }

  // ── 纯文本 fallback（带字符偏移高亮） ─────────────────────────────────────
  const text = segment.sourceText
  let content: React.ReactNode

  if (highlight) {
    const { start, end } = highlight
    content = (
      <>
        {text.slice(0, start)}
        <mark className="bg-yellow-200 rounded px-0.5">{text.slice(start, end)}</mark>
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
      data-side="source"
      className="cursor-text select-text whitespace-pre-wrap"
      onDoubleClick={() => setEditing(true)}
    >
      {content}
    </ParaBlock>
  )
}
