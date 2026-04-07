/**
 * SelectionHighlighter：监听 mouseup，提取并设置当前 selection 状态。
 * 挂载在 SegmentList 容器外层，统一捕获 source/target 两侧的 selection 事件。
 */
import { useEffect, type ReactNode } from 'react'
import { getNormalizedSelection, type NormalizedSelection } from '../lib/selection'

interface Props {
  children: ReactNode
  onSelect: (sel: NormalizedSelection | null) => void
}

export default function SelectionHighlighter({ children, onSelect }: Props) {
  useEffect(() => {
    function handleMouseUp() {
      const sel = getNormalizedSelection()
      onSelect(sel)
    }
    document.addEventListener('mouseup', handleMouseUp)
    return () => document.removeEventListener('mouseup', handleMouseUp)
  }, [onSelect])

  return <>{children}</>
}
