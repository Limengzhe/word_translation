/**
 * SegmentList：虚拟化列表（react-virtual）
 * 渲染所有 SegmentRow，支持高性能长文。
 */
import { useRef } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'
import SegmentRow from './SegmentRow'
import type { SegmentDto } from '../types/contract'
import type { NormalizedSelection } from '../lib/selection'

interface Props {
  segments: (SegmentDto & { _streamingText?: string })[]
  docId: string
  selection?: NormalizedSelection
  onSaveSource: (segmentId: string, text: string) => void
  onSyncTranslation: (segmentId: string) => void
  onSaveTarget: (segmentId: string, text: string) => void
  onRewrite: (segmentId: string) => void
  onAccept: (revisionId: string) => void
  onReject: (revisionId: string) => void
}

export default function SegmentList({
  segments,
  docId,
  selection,
  onSaveSource,
  onSyncTranslation,
  onSaveTarget,
  onRewrite,
  onAccept,
  onReject,
}: Props) {
  const parentRef = useRef<HTMLDivElement>(null)

  const virtualizer = useVirtualizer({
    count: segments.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 80,
    overscan: 10,
  })

  return (
    <div ref={parentRef} className="h-full overflow-y-auto scrollbar-thin">
      <div
        style={{ height: `${virtualizer.getTotalSize()}px`, position: 'relative' }}
      >
        {virtualizer.getVirtualItems().map((item) => {
          const seg = segments[item.index]
          return (
            <div
              key={seg.id}
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                transform: `translateY(${item.start}px)`,
              }}
              ref={virtualizer.measureElement}
              data-index={item.index}
            >
              <SegmentRow
                segment={seg}
                docId={docId}
                selection={selection}
                onSaveSource={(text) => onSaveSource(seg.id, text)}
                onSyncTranslation={() => onSyncTranslation(seg.id)}
                onSaveTarget={(text) => onSaveTarget(seg.id, text)}
                onRewrite={() => onRewrite(seg.id)}
                onAccept={() => seg.pendingRevisionId && onAccept(seg.pendingRevisionId)}
                onReject={() => seg.pendingRevisionId && onReject(seg.pendingRevisionId)}
              />
            </div>
          )
        })}
      </div>
    </div>
  )
}
