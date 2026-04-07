/**
 * Selection 映射工具：
 * 1. 从 DOM selection 提取 {segmentId, side, startOffset, endOffset}
 * 2. 将一侧 offset 按比例映射到另一侧句子的估算 offset
 */

export type SelectionSide = 'source' | 'target'

export interface NormalizedSelection {
  segmentId: string
  side: SelectionSide
  startOffset: number
  endOffset: number
}

/**
 * 从当前 window.getSelection() 提取归一化 selection。
 * 要求被选中的 DOM 节点上有 data-segment-id 和 data-side 属性。
 */
export function getNormalizedSelection(): NormalizedSelection | null {
  const sel = window.getSelection()
  if (!sel || sel.isCollapsed || !sel.rangeCount) return null

  const range = sel.getRangeAt(0)
  const container = range.startContainer.parentElement

  // 向上查找带有 data-segment-id 的祖先
  let el: Element | null = container
  while (el && !el.getAttribute('data-segment-id')) {
    el = el.parentElement
  }
  if (!el) return null

  const segmentId = el.getAttribute('data-segment-id')!
  const side = (el.getAttribute('data-side') as SelectionSide | null) ?? 'source'

  // 计算纯文本偏移量
  const textContent = el.textContent ?? ''
  const preSelRange = document.createRange()
  preSelRange.setStart(el, 0)
  preSelRange.setEnd(range.startContainer, range.startOffset)
  const startOffset = preSelRange.toString().length
  const endOffset = startOffset + range.toString().length

  return { segmentId, side, startOffset, endOffset }
}

/**
 * 比例映射：将一侧的 [start, end] 映射到另一侧句子的估算 [start, end]。
 */
export function mapOffsets(
  startOffset: number,
  endOffset: number,
  fromLen: number,
  toLen: number,
): { start: number; end: number } {
  if (fromLen === 0 || toLen === 0) return { start: 0, end: toLen }
  const ratio = toLen / fromLen
  return {
    start: Math.floor(startOffset * ratio),
    end: Math.min(Math.ceil(endOffset * ratio), toLen),
  }
}
