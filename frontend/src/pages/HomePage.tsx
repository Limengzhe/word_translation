/**
 * HomePage：上传 .docx 文件，用 Mammoth 解析后创建翻译文档。
 * 存储完整 HTML（fullSourceHtml），用于左栏原样渲染。
 * 也支持直接粘贴纯文本（fallback）。
 */
import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { parseDocx, type ParseDocxResult } from '../lib/docx/parseDocx'
import { useCreateDocument } from '../features/document/hooks'

const LANG_OPTIONS = [
  { value: 'en', label: 'English' },
  { value: 'zh', label: '中文' },
  { value: 'ja', label: '日本語' },
  { value: 'fr', label: 'Français' },
  { value: 'de', label: 'Deutsch' },
  { value: 'es', label: 'Español' },
  { value: 'ko', label: '한국어' },
]

type InputMode = 'file' | 'text'

export default function HomePage() {
  const navigate = useNavigate()
  const create = useCreateDocument()
  const fileRef = useRef<HTMLInputElement>(null)

  const [mode, setMode] = useState<InputMode>('file')
  const [sourceLang, setSourceLang] = useState('zh')
  const [targetLang, setTargetLang] = useState('en')

  const [fileName, setFileName] = useState('')
  const [parsed, setParsed] = useState<ParseDocxResult | null>(null)
  const [parsing, setParsing] = useState(false)
  const [parseError, setParseError] = useState('')

  const [sourceText, setSourceText] = useState('')

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    if (!file.name.endsWith('.docx')) {
      setParseError('请选择 .docx 格式的 Word 文件')
      return
    }
    setParseError('')
    setParsing(true)
    setFileName(file.name)
    try {
      const buf = await file.arrayBuffer()
      const result = await parseDocx(buf)
      setParsed(result)
    } catch (err) {
      setParseError(`解析失败：${(err as Error).message}`)
      setParsed(null)
    } finally {
      setParsing(false)
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()

    const body =
      mode === 'file' && parsed
        ? {
            sourceLang,
            targetLang,
            fullSourceHtml: parsed.fullHtml,
            settings: { provider: 'openai' as const, model: 'qwen-plus', temperature: 0.2 },
          }
        : {
            sourceLang,
            targetLang,
            sourceText,
            settings: { provider: 'openai' as const, model: 'qwen-plus', temperature: 0.2 },
          }

    const res = await create.mutateAsync(body)
    navigate(`/doc/${res.document.id}`)
  }

  const canSubmit =
    !create.isPending &&
    (mode === 'file' ? parsed !== null : sourceText.trim().length > 0)

  return (
    <div className="h-full flex items-center justify-center p-8 bg-gray-50">
      <div className="w-full max-w-2xl">
        <h1 className="text-2xl font-bold text-gray-800 mb-2">新建翻译文档</h1>
        <p className="text-sm text-gray-500 mb-6">上传 Word 文件，完整保留原始排版进行对照翻译</p>

        <form onSubmit={handleSubmit} className="bg-white rounded-2xl shadow-sm border border-gray-200 p-6 space-y-5">
          {/* 语言选择 */}
          <div className="flex gap-4 items-end">
            <div className="flex-1">
              <label className="block text-xs font-medium text-gray-500 mb-1">原文语言</label>
              <select value={sourceLang} onChange={e => setSourceLang(e.target.value)}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300">
                {LANG_OPTIONS.map(l => <option key={l.value} value={l.value}>{l.label}</option>)}
              </select>
            </div>
            <div className="pb-2 text-gray-400 text-lg">→</div>
            <div className="flex-1">
              <label className="block text-xs font-medium text-gray-500 mb-1">目标语言</label>
              <select value={targetLang} onChange={e => setTargetLang(e.target.value)}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300">
                {LANG_OPTIONS.map(l => <option key={l.value} value={l.value}>{l.label}</option>)}
              </select>
            </div>
          </div>

          {/* 输入方式切换 */}
          <div className="flex gap-2 border-b border-gray-100 pb-3">
            {(['file', 'text'] as InputMode[]).map(m => (
              <button key={m} type="button" onClick={() => setMode(m)}
                className={`px-3 py-1 rounded-lg text-sm transition-colors ${
                  mode === m ? 'bg-indigo-600 text-white' : 'text-gray-500 hover:bg-gray-100'
                }`}>
                {m === 'file' ? '📄 上传 Word 文件' : '📝 粘贴纯文本'}
              </button>
            ))}
          </div>

          {/* 文件上传区 */}
          {mode === 'file' && (
            <div>
              <input ref={fileRef} type="file" accept=".docx" className="hidden"
                onChange={handleFileChange} />

              {!parsed ? (
                <button type="button" onClick={() => fileRef.current?.click()}
                  disabled={parsing}
                  className="w-full h-36 border-2 border-dashed border-gray-200 rounded-xl flex flex-col items-center justify-center gap-2 text-gray-400 hover:border-indigo-300 hover:text-indigo-500 transition-colors">
                  {parsing ? (
                    <>
                      <span className="text-2xl animate-spin">⟳</span>
                      <span className="text-sm">解析中…</span>
                    </>
                  ) : (
                    <>
                      <span className="text-3xl">📄</span>
                      <span className="text-sm font-medium">点击上传 .docx 文件</span>
                      <span className="text-xs">支持 Word 2007+ 格式，完整保留表格/标题等排版</span>
                    </>
                  )}
                </button>
              ) : (
                <div className="border border-green-200 bg-green-50 rounded-xl p-4">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <span className="text-green-600">✓</span>
                      <span className="text-sm font-medium text-green-800">{fileName}</span>
                    </div>
                    <button type="button"
                      onClick={() => { setParsed(null); setFileName(''); if (fileRef.current) fileRef.current.value = '' }}
                      className="text-xs text-gray-400 hover:text-red-400">重新选择</button>
                  </div>
                  <p className="text-xs text-gray-500 mb-3">
                    已解析 {parsed.paragraphs.length} 个段落，HTML 大小 {Math.round(parsed.fullHtml.length / 1024)} KB
                  </p>
                  {/* 预览前 200 字符的 HTML 渲染效果 */}
                  <div
                    className="word-format text-xs text-gray-700 max-h-32 overflow-y-auto bg-white rounded-lg p-2 border border-green-100"
                    dangerouslySetInnerHTML={{ __html: parsed.fullHtml }}
                  />
                </div>
              )}

              {parseError && (
                <p className="text-sm text-red-500 mt-2">{parseError}</p>
              )}
            </div>
          )}

          {/* 纯文本 fallback */}
          {mode === 'text' && (
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">原文内容</label>
              <textarea value={sourceText} onChange={e => setSourceText(e.target.value)}
                placeholder="在此粘贴需要翻译的文本…"
                className="w-full h-44 border border-gray-200 rounded-xl px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-indigo-300" />
            </div>
          )}

          <button type="submit" disabled={!canSubmit}
            className="w-full py-2.5 bg-indigo-600 text-white rounded-xl text-sm font-medium hover:bg-indigo-700 disabled:opacity-40 transition-colors">
            {create.isPending ? '创建中…' : '创建文档 →'}
          </button>

          {create.isError && (
            <p className="text-sm text-red-500">{(create.error as Error).message}</p>
          )}
        </form>
      </div>
    </div>
  )
}
