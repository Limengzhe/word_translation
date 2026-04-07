/**
 * 字符级 diff，输出 DiffOp[] 供 DiffView 渲染。
 * 使用 diff-match-patch 以获得高质量差分结果。
 */
import DiffMatchPatch from 'diff-match-patch'
import type { DiffOp } from '../../types/contract'

const dmp = new DiffMatchPatch()

export function computeDiff(baseText: string, proposedText: string): DiffOp[] {
  const diffs = dmp.diff_main(baseText, proposedText)
  dmp.diff_cleanupSemantic(diffs)

  return diffs.map(([op, text]) => {
    if (op === DiffMatchPatch.DIFF_EQUAL) return { type: 'equal', text }
    if (op === DiffMatchPatch.DIFF_INSERT) return { type: 'insert', text }
    return { type: 'delete', text }
  })
}
