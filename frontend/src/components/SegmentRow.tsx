/**
 * SegmentRow：双栏段落行
 * - 行高自适应内容（段落/标题行高不同）
 * - 行级颜色：source_edited=红，syncing=橙
 * - 操作按钮悬停显示
 */
import clsx from 'clsx'
import SourceCell from './SourceCell'
import TargetCell from './TargetCell'
import type { SegmentDto } from '../types/contract'
import { mapOffsets } from '../lib/selection'
import type { NormalizedSelection } from '../lib/selection'

interface Props {
  segment: SegmentDto & { _streamingText?: string }
  docId: string
  selection?: NormalizedSelection
  onSaveSource: (text: string) => void
  onSyncTranslation: () => void
  onSaveTarget: (text: string) => void
  onRewrite: () => void
  onAccept: () => void
  onReject: () => void
}

export default function SegmentRow({
  segment, docId, selection,
  onSaveSource, onSyncTranslation, onSaveTarget,
  onRewrite, onAccept, onReject,
}: Props) {
  const isEdited  = segment.sourceStatus === 'source_edited'
  const isSyncing = segment.sourceStatus === 'syncing' || segment._streamingText !== undefined
  const hasPending = !!segment.pendingRevisionId

  const rowClass = clsx(
    'flex group border-b border-gray-100 transition-colors',
    isEdited  && 'bg-red-50 border-l-[3px] border-l-red-400',
    isSyncing && 'bg-orange-50 border-l-[3px] border-l-orange-400',
    !isEdited && !isSyncing && 'hover:bg-gray-50/60',
  )

  // 计算高亮范围
  const sourceLen = segment.sourceText.length
  const targetLen = segment.currentText.length
  let sourceHL: { start: number; end: number; strong: boolean } | undefined
  let targetHL: { start: number; end: number; strong: boolean } | undefined

  if (selection?.segmentId === segment.id) {
    if (selection.side === 'source') {
      sourceHL = { start: selection.startOffset, end: selection.endOffset, strong: false }
      const m = mapOffsets(selection.startOffset, selection.endOffset, sourceLen, targetLen)
      targetHL = { ...m, strong: true }
    } else {
      targetHL = { start: selection.startOffset, end: selection.endOffset, strong: false }
      const m = mapOffsets(selection.startOffset, selection.endOffset, targetLen, sourceLen)
      sourceHL = { ...m, strong: true }
    }
  }

  return (
    <div className={rowClass}>
      {/* 行号 */}
      <div className="w-7 shrink-0 pt-3 text-center text-xs text-gray-300 select-none">
        {segment.index + 1}
      </div>

      {/* 左栏：原文 */}
      <div className="flex-1 min-w-0 px-4 py-3 border-r border-gray-100">
        <SourceCell segment={segment} highlight={sourceHL} onSave={onSaveSource} />
        {/* 同步翻译按钮（仅 source_edited 时显示） */}
        {isEdited && (
          <div className="mt-2">
            <button onClick={onSyncTranslation} disabled={isSyncing}
              className="px-2.5 py-1 rounded text-xs bg-orange-500 text-white hover:bg-orange-600 disabled:opacity-50">
              同步翻译
            </button>
          </div>
        )}
      </div>

      {/* 右栏：译文 */}
      <div className="flex-1 min-w-0 px-4 py-3">
        <TargetCell segment={segment} docId={docId} highlight={targetHL} onSaveEdit={onSaveTarget} />
        {/* 操作按钮（悬停显示） */}
        <div className="mt-1.5 flex gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
          {hasPending ? (
            <>
              <button onClick={onAccept}
                className="px-2.5 py-0.5 rounded text-xs bg-green-500 text-white hover:bg-green-600">
                ✓ 接受
              </button>
              <button onClick={onReject}
                className="px-2.5 py-0.5 rounded text-xs bg-gray-200 text-gray-600 hover:bg-gray-300">
                ✕ 拒绝
              </button>
            </>
          ) : (
            <button onClick={onRewrite}
              className="px-2.5 py-0.5 rounded text-xs bg-indigo-100 text-indigo-600 hover:bg-indigo-200">
              AI 改写
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
