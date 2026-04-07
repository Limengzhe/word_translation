/**
 * DocumentEditorPage：全文对照翻译 + 流式实时渲染 + 可编辑 + 双向对应高亮
 *
 * 高亮原理：
 *   LLM 被要求严格保留 HTML 标签结构，因此左右两栏的 block 元素（p/td/h1-h6/li 等）
 *   在 DOM 中的出现顺序一一对应。选中任一栏的文字后，定位其所属 block 元素的索引，
 *   在另一栏找到同索引 block 高亮，并用 SVG 虚线贝塞尔曲线连接。
 */
import { useEffect, useRef, useCallback, useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  useDocument,
  useTranslateFullStream,
  usePatchFullHtml,
} from '../features/document/hooks'

// ── 高亮辅助 ──────────────────────────────────────────────────────────────────

const BLOCK_SEL = 'p, h1, h2, h3, h4, h5, h6, li, td, th, blockquote, pre'
const HL_CLASS = 'correspondence-hl'

function getBlocks(container: HTMLElement): HTMLElement[] {
  return Array.from(container.querySelectorAll<HTMLElement>(BLOCK_SEL))
}

function findBlock(node: Node, container: HTMLElement): HTMLElement | null {
  let el: HTMLElement | null = node instanceof HTMLElement ? node : node.parentElement
  while (el && el !== container) {
    if (el.matches(BLOCK_SEL)) return el
    el = el.parentElement
  }
  return null
}

// ── 组件 ──────────────────────────────────────────────────────────────────────

export default function DocumentEditorPage() {
  const { docId } = useParams<{ docId: string }>()
  const { data, isLoading, error } = useDocument(docId!)
  const translate = useTranslateFullStream(docId!)
  const patch = usePatchFullHtml(docId!)

  const leftRef = useRef<HTMLDivElement>(null)
  const rightRef = useRef<HTMLDivElement>(null)
  const wrapperRef = useRef<HTMLDivElement>(null)
  const svgRef = useRef<SVGSVGElement>(null)

  const hlRef = useRef<{ src: HTMLElement | null; tgt: HTMLElement | null }>({
    src: null,
    tgt: null,
  })
  const isTranslatingRef = useRef(false)
  isTranslatingRef.current = translate.isTranslating

  const [savingLeft, setSavingLeft] = useState(false)
  const [savingRight, setSavingRight] = useState(false)

  // ── 将右栏 DOM 元素注册到 hook，token 直接写 DOM ──
  useEffect(() => {
    translate.setTargetEl(rightRef.current)
  }, [translate.setTargetEl])

  // ── 左栏初始化 ──
  const leftInited = useRef(false)
  useEffect(() => {
    if (leftRef.current && data?.document.fullSourceHtml && !leftInited.current) {
      leftRef.current.innerHTML = data.document.fullSourceHtml
      leftInited.current = true
    }
  }, [data?.document.fullSourceHtml])

  // ── 右栏：已有译文初始化（非流式场景） ──
  const rightInited = useRef(false)
  useEffect(() => {
    if (!rightRef.current) return
    if (!translate.isTranslating && data?.document.fullTranslatedHtml && !rightInited.current) {
      rightRef.current.innerHTML = data.document.fullTranslatedHtml
      rightInited.current = true
    }
  }, [translate.isTranslating, data?.document.fullTranslatedHtml])

  // ── 翻译开始时清除高亮 ──
  useEffect(() => {
    if (translate.isTranslating && svgRef.current) {
      svgRef.current.innerHTML = ''
    }
  }, [translate.isTranslating])

  // ── 保存 ──
  const saveLeft = useCallback(async () => {
    if (!leftRef.current) return
    setSavingLeft(true)
    try { await patch.mutateAsync({ fullSourceHtml: leftRef.current.innerHTML }) }
    finally { setSavingLeft(false) }
  }, [patch])

  const saveRight = useCallback(async () => {
    if (!rightRef.current) return
    setSavingRight(true)
    try { await patch.mutateAsync({ fullTranslatedHtml: rightRef.current.innerHTML }) }
    finally { setSavingRight(false) }
  }, [patch])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault()
        saveLeft()
        saveRight()
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [saveLeft, saveRight])

  // ── 双向对应高亮 + SVG 虚线 ──
  useEffect(() => {
    let rafId = 0

    function clearHl() {
      hlRef.current.src?.classList.remove(HL_CLASS)
      hlRef.current.tgt?.classList.remove(HL_CLASS)
      hlRef.current = { src: null, tgt: null }
      if (svgRef.current) svgRef.current.innerHTML = ''
    }

    function drawLine() {
      const { src, tgt } = hlRef.current
      if (!src || !tgt || !wrapperRef.current || !svgRef.current) return

      const wr = wrapperRef.current.getBoundingClientRect()
      const sr = src.getBoundingClientRect()
      const tr = tgt.getBoundingClientRect()

      const wH = wr.height
      const clampY = (v: number) => Math.max(0, Math.min(wH, v))

      const x1 = sr.right - wr.left
      const y1 = clampY(sr.top + sr.height / 2 - wr.top)
      const x2 = tr.left - wr.left
      const y2 = clampY(tr.top + tr.height / 2 - wr.top)
      const cx = (x1 + x2) / 2

      svgRef.current.innerHTML =
        `<circle cx="${x1}" cy="${y1}" r="3" fill="#6366f1" opacity="0.5"/>` +
        `<path d="M ${x1} ${y1} C ${cx} ${y1}, ${cx} ${y2}, ${x2} ${y2}" ` +
        `stroke="#6366f1" stroke-width="1.5" stroke-dasharray="6 4" fill="none" opacity="0.5"/>` +
        `<circle cx="${x2}" cy="${y2}" r="3" fill="#6366f1" opacity="0.5"/>`
    }

    function handleHighlight() {
      if (isTranslatingRef.current) return

      const sel = window.getSelection()
      if (!sel || sel.isCollapsed || !sel.anchorNode) {
        clearHl()
        return
      }

      const anchor = sel.anchorNode
      const inLeft = leftRef.current?.contains(anchor)
      const inRight = rightRef.current?.contains(anchor)
      if (!inLeft && !inRight) { clearHl(); return }

      const srcPane = inLeft ? leftRef.current! : rightRef.current!
      const tgtPane = inLeft ? rightRef.current! : leftRef.current!

      const block = findBlock(anchor, srcPane)
      if (!block) { clearHl(); return }

      const srcBlocks = getBlocks(srcPane)
      const idx = srcBlocks.indexOf(block)
      if (idx === -1) { clearHl(); return }

      const tgtBlocks = getBlocks(tgtPane)
      const tgtBlock = tgtBlocks[idx]
      if (!tgtBlock) { clearHl(); return }

      clearHl()

      block.classList.add(HL_CLASS)
      tgtBlock.classList.add(HL_CLASS)

      if (inLeft) {
        hlRef.current = { src: block, tgt: tgtBlock }
      } else {
        hlRef.current = { src: tgtBlock, tgt: block }
      }
      drawLine()
    }

    const onSelChange = () => {
      cancelAnimationFrame(rafId)
      rafId = requestAnimationFrame(handleHighlight)
    }

    let scrollRaf = 0
    const onScroll = () => {
      cancelAnimationFrame(scrollRaf)
      scrollRaf = requestAnimationFrame(drawLine)
    }

    document.addEventListener('selectionchange', onSelChange)
    // scroll 不冒泡，但会在捕获阶段传播；挂到 document 捕获阶段
    // 可以捕获任意子元素的滚动，无需等待具体 DOM 挂载
    document.addEventListener('scroll', onScroll, { capture: true, passive: true })
    window.addEventListener('resize', onScroll)

    return () => {
      document.removeEventListener('selectionchange', onSelChange)
      document.removeEventListener('scroll', onScroll, { capture: true })
      window.removeEventListener('resize', onScroll)
      cancelAnimationFrame(rafId)
      cancelAnimationFrame(scrollRaf)
      clearHl()
    }
  }, [])

  // ── 渲染 ──
  if (isLoading) return <div className="flex items-center justify-center h-full text-gray-400">加载中…</div>
  if (error) return <div className="flex items-center justify-center h-full text-red-400">{(error as Error).message}</div>
  if (!data) return null

  const { document: doc } = data
  const hasTranslation = !!(translate.finalHtmlRef.current || doc.fullTranslatedHtml)

  return (
    <div className="flex flex-col h-full">
      {/* 顶部栏 */}
      <div className="flex items-center gap-4 px-6 py-3 bg-white border-b border-gray-200 shrink-0">
        <span className="text-sm font-medium text-gray-700">
          {doc.sourceLang.toUpperCase()} → {doc.targetLang.toUpperCase()}
        </span>
        <div className="flex-1" />
        {(savingLeft || savingRight) && (
          <span className="text-xs text-gray-400 animate-pulse">保存中…</span>
        )}
        <span className="text-xs text-gray-400">Ctrl+S 保存 · 选中文字查看对应关系</span>

        {translate.isTranslating ? (
          <div className="flex items-center gap-2 text-sm text-indigo-600">
            <span className="animate-spin inline-block">⟳</span>
            <span>{translate.progressText || '翻译中…'}</span>
            <button onClick={translate.stop} className="text-gray-400 hover:text-gray-600 text-xs ml-1">
              停止
            </button>
          </div>
        ) : (
          <button
            onClick={() => translate.start()}
            className="px-4 py-1.5 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 transition-colors"
          >
            {hasTranslation ? '重新翻译' : '开始翻译'}
          </button>
        )}
      </div>

      {/* 列头 */}
      <div className="flex bg-gray-50 border-b border-gray-200 text-xs font-medium text-gray-500 shrink-0">
        <div className="flex-1 px-6 py-2 border-r border-gray-200">原文 ({doc.sourceLang})</div>
        <div className="flex-1 px-6 py-2">译文 ({doc.targetLang})</div>
      </div>

      {/* 内容双栏 + SVG 连线层 */}
      <div ref={wrapperRef} className="flex flex-1 overflow-hidden relative">
        <svg
          ref={svgRef}
          className="absolute inset-0 pointer-events-none z-20"
          style={{ width: '100%', height: '100%' }}
        />

        {/* 左栏：原文 */}
        <div
          ref={leftRef}
          contentEditable
          suppressContentEditableWarning
          onBlur={saveLeft}
          className="flex-1 overflow-y-auto border-r border-gray-200 px-8 py-6 word-format prose prose-sm max-w-none outline-none focus:ring-2 focus:ring-inset focus:ring-indigo-200"
        />

        {/* 右栏：译文 */}
        <div className="flex-1 overflow-y-auto relative">
          <div
            ref={rightRef}
            contentEditable={!translate.isTranslating}
            suppressContentEditableWarning
            onBlur={saveRight}
            className="h-full px-8 py-6 word-format prose prose-sm max-w-none outline-none focus:ring-2 focus:ring-inset focus:ring-indigo-200"
          />
          {!translate.isTranslating && !hasTranslation && (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-gray-400 pointer-events-none">
              <span className="text-4xl">📝</span>
              <p className="text-sm">点击「开始翻译」，翻译结果将实时输出</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
