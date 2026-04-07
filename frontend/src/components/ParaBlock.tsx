/**
 * ParaBlock：根据 paraType 用对应的 HTML 标签渲染文本，
 * 保持与 Word 原文档一致的视觉结构。
 */
import type { ReactNode } from 'react'
import clsx from 'clsx'
import type { ParaType } from '../types/contract'

const STYLE_MAP: Record<ParaType, string> = {
  h1: 'text-2xl font-bold leading-snug text-gray-900',
  h2: 'text-xl font-bold leading-snug text-gray-800',
  h3: 'text-lg font-semibold leading-snug text-gray-800',
  h4: 'text-base font-semibold text-gray-800',
  h5: 'text-sm font-semibold text-gray-700',
  h6: 'text-sm font-medium text-gray-600',
  p:  'text-sm leading-relaxed text-gray-700',
  li: 'text-sm leading-relaxed text-gray-700 pl-4 before:content-["•"] before:mr-2 before:text-gray-400',
  blockquote: 'text-sm leading-relaxed text-gray-600 italic border-l-4 border-gray-300 pl-3',
  pre: 'text-xs font-mono leading-relaxed text-gray-700 bg-gray-50 rounded px-2 py-1',
}

interface Props {
  paraType: ParaType
  children: ReactNode
  className?: string
  'data-segment-id'?: string
  'data-side'?: string
  onDoubleClick?: () => void
}

export default function ParaBlock({ paraType, children, className, ...rest }: Props) {
  const base = STYLE_MAP[paraType] ?? STYLE_MAP.p
  const Tag = (['h1','h2','h3','h4','h5','h6'].includes(paraType) ? paraType : 'div') as keyof JSX.IntrinsicElements

  return (
    <Tag className={clsx(base, className)} {...rest}>
      {children}
    </Tag>
  )
}
