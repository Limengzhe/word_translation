/**
 * DiffView：将 DiffOp[] 渲染为带颜色标记的内联 span 列表。
 * - delete：红色删除线
 * - insert：绿色背景
 * - equal ：普通文本
 */
import type { DiffOp } from '../types/contract'

interface Props {
  ops: DiffOp[]
}

export default function DiffView({ ops }: Props) {
  return (
    <span>
      {ops.map((op, i) => {
        if (op.type === 'equal') {
          return <span key={i}>{op.text}</span>
        }
        if (op.type === 'delete') {
          return (
            <span
              key={i}
              className="bg-red-100 text-red-700 line-through"
            >
              {op.text}
            </span>
          )
        }
        // insert
        return (
          <span key={i} className="bg-green-100 text-green-800">
            {op.text}
          </span>
        )
      })}
    </span>
  )
}
