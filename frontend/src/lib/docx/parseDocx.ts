/**
 * parseDocx：使用 Mammoth.js 解析 .docx。
 *
 * 返回：
 *   fullHtml    — Mammoth 输出的完整 HTML（含表格/标题/列表等原始排版，用于左栏渲染）
 *   paragraphs  — 段落列表（text + paraType，供翻译对照用，可选）
 */
import mammoth from 'mammoth'

export type ParaType =
  | 'h1' | 'h2' | 'h3' | 'h4' | 'h5' | 'h6'
  | 'p' | 'li' | 'blockquote' | 'pre'

export interface ParsedParagraph {
  text: string
  paraType: ParaType
  sourceHtml: string
}

export interface ParseDocxResult {
  /** Mammoth 输出的完整 HTML（含表格等完整排版） */
  fullHtml: string
  /** 按块元素拆出的段落（text / paraType），可选用于翻译 */
  paragraphs: ParsedParagraph[]
}

const BLOCK_TAGS: ParaType[] = [
  'h1','h2','h3','h4','h5','h6','p','li','blockquote','pre',
]

function tagToParaType(tag: string): ParaType {
  if ((BLOCK_TAGS as string[]).includes(tag)) return tag as ParaType
  return 'p'
}

/** 从 Element 提取内层 HTML */
function innerHtml(el: Element): string {
  return el.innerHTML
}

function extractParagraphs(body: HTMLElement): ParsedParagraph[] {
  const paragraphs: ParsedParagraph[] = []

  function processNode(node: Element) {
    const tag = node.tagName.toLowerCase()

    if (tag === 'ul' || tag === 'ol') {
      node.querySelectorAll(':scope > li').forEach(li => {
        const text = li.textContent?.trim() ?? ''
        if (text) paragraphs.push({ text, paraType: 'li', sourceHtml: innerHtml(li) })
      })
      return
    }

    // 表格：整个 <table> 合并为一个段落（保留完整文本）
    if (tag === 'table') {
      const text = Array.from(node.querySelectorAll('td,th'))
        .map(c => c.textContent?.trim())
        .filter(Boolean)
        .join(' | ')
      if (text) {
        paragraphs.push({ text, paraType: 'p', sourceHtml: node.outerHTML })
      }
      return
    }

    const text = node.textContent?.trim() ?? ''
    if (!text) return
    paragraphs.push({ text, paraType: tagToParaType(tag), sourceHtml: innerHtml(node) })
  }

  Array.from(body.children).forEach(child => processNode(child))
  return paragraphs
}

/** 将 docx 内嵌图片转为 base64 data URI，确保 HTML 中 img 可直接显示 */
const convertImage = mammoth.images.imgElement(function (image: any) {
  return image.read('base64').then(function (imageBuffer: string) {
    return { src: `data:${image.contentType};base64,${imageBuffer}` }
  })
})

/** 解析 .docx ArrayBuffer */
export async function parseDocx(buffer: ArrayBuffer): Promise<ParseDocxResult> {
  const result = await mammoth.convertToHtml({
    arrayBuffer: buffer,
  }, { convertImage })

  const warnings = result.messages.filter(m => m.type === 'warning')
  if (warnings.length > 0) {
    console.warn('[parseDocx] Mammoth warnings:', warnings.map(m => m.message))
  }

  const fullHtml = result.value

  const parser = new DOMParser()
  const doc = parser.parseFromString(`<body>${fullHtml}</body>`, 'text/html')
  const paragraphs = extractParagraphs(doc.body)

  const imgCount = (fullHtml.match(/<img\b/gi) || []).length
  console.log(`[parseDocx] fullHtml length=${fullHtml.length}, paragraphs=${paragraphs.length}, images=${imgCount}`)
  return { fullHtml, paragraphs }
}
