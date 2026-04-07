/**
 * SkillsPage：Skills 管理界面
 * - 左侧：SkillSet 列表
 * - 右侧：选中 SkillSet 的 Glossary + HabitRules + 提炼操作
 */
import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  useSkillSets,
  useSkillSet,
  useCreateSkillSet,
  useAddGlossaryEntry,
  useDeleteGlossaryEntry,
  useAddHabitRule,
  useDeleteHabitRule,
  useExtract,
} from '../features/skills/hooks'

export default function SkillsPage() {
  const { skillSetId } = useParams<{ skillSetId?: string }>()
  const navigate = useNavigate()

  const { data: skillSets = [] } = useSkillSets()
  const { data: detail, isLoading } = useSkillSet(skillSetId)

  const createSet = useCreateSkillSet()
  const addEntry = useAddGlossaryEntry(skillSetId ?? '')
  const delEntry = useDeleteGlossaryEntry(skillSetId ?? '')
  const addHabit = useAddHabitRule(skillSetId ?? '')
  const delHabit = useDeleteHabitRule(skillSetId ?? '')
  const extract = useExtract(skillSetId ?? '')

  const [newSetName, setNewSetName] = useState('')
  const [newSetScope, setNewSetScope] = useState<'universal' | 'lang_pair'>('universal')
  const [newSetSrcLang, setNewSetSrcLang] = useState('en')
  const [newSetTgtLang, setNewSetTgtLang] = useState('zh')

  const [newSrcTerm, setNewSrcTerm] = useState('')
  const [newTgtTerm, setNewTgtTerm] = useState('')
  const [newDomain, setNewDomain] = useState('')

  const [newHabit, setNewHabit] = useState('')
  const [extractResult, setExtractResult] = useState<string | null>(null)

  return (
    <div className="flex h-full">
      {/* 左侧列表 */}
      <div className="w-64 shrink-0 border-r border-gray-200 bg-white flex flex-col">
        <div className="px-4 py-3 border-b border-gray-100 text-sm font-medium text-gray-700">
          Skills 集合
        </div>

        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {skillSets.map((ss) => (
            <button
              key={ss.id}
              onClick={() => navigate(`/skills/${ss.id}`)}
              className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                ss.id === skillSetId
                  ? 'bg-indigo-50 text-indigo-700 font-medium'
                  : 'text-gray-700 hover:bg-gray-50'
              }`}
            >
              <div className="font-medium truncate">{ss.name}</div>
              <div className="text-xs text-gray-400 mt-0.5">
                {ss.scope === 'universal' ? '通用' : `${ss.sourceLang}→${ss.targetLang}`}
              </div>
            </button>
          ))}
        </div>

        {/* 新建 SkillSet */}
        <div className="p-3 border-t border-gray-100 space-y-2">
          <input
            value={newSetName}
            onChange={(e) => setNewSetName(e.target.value)}
            placeholder="新 Skills 名称"
            className="w-full border border-gray-200 rounded px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-indigo-300"
          />
          <select
            value={newSetScope}
            onChange={(e) => setNewSetScope(e.target.value as any)}
            className="w-full border border-gray-200 rounded px-2 py-1.5 text-xs focus:outline-none"
          >
            <option value="universal">通用（所有语种）</option>
            <option value="lang_pair">指定语种对</option>
          </select>
          {newSetScope === 'lang_pair' && (
            <div className="flex gap-1">
              <input value={newSetSrcLang} onChange={(e) => setNewSetSrcLang(e.target.value)}
                className="flex-1 border border-gray-200 rounded px-2 py-1 text-xs focus:outline-none" placeholder="en" />
              <span className="text-gray-400 self-center">→</span>
              <input value={newSetTgtLang} onChange={(e) => setNewSetTgtLang(e.target.value)}
                className="flex-1 border border-gray-200 rounded px-2 py-1 text-xs focus:outline-none" placeholder="zh" />
            </div>
          )}
          <button
            onClick={() => {
              if (!newSetName.trim()) return
              createSet.mutate({
                name: newSetName.trim(),
                scope: newSetScope,
                sourceLang: newSetScope === 'lang_pair' ? newSetSrcLang : undefined,
                targetLang: newSetScope === 'lang_pair' ? newSetTgtLang : undefined,
              })
              setNewSetName('')
            }}
            disabled={createSet.isPending}
            className="w-full py-1.5 text-xs bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50"
          >
            创建
          </button>
        </div>
      </div>

      {/* 右侧详情 */}
      <div className="flex-1 overflow-y-auto p-6">
        {!skillSetId && (
          <p className="text-gray-400 text-sm mt-8 text-center">← 选择或创建一个 Skills 集合</p>
        )}
        {skillSetId && isLoading && <p className="text-gray-400 text-sm">加载中…</p>}

        {detail && (
          <div className="max-w-3xl space-y-8">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-800">{detail.skillSet.name}</h2>
              <div className="flex items-center gap-2">
                <button
                  onClick={async () => {
                    const r = await extract.mutateAsync(50)
                    setExtractResult(`提炼完成：处理 ${r.extractedCount} 条，新增词表 ${r.addedGlossary} 项，新增习惯 ${r.addedHabits} 条`)
                  }}
                  disabled={extract.isPending}
                  className="px-3 py-1.5 text-sm bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50"
                >
                  {extract.isPending ? '提炼中…' : '从编辑记录提炼'}
                </button>
              </div>
            </div>

            {extractResult && (
              <div className="text-sm text-purple-700 bg-purple-50 border border-purple-200 rounded-lg px-4 py-2">
                {extractResult}
              </div>
            )}

            {/* 词表 */}
            <section>
              <h3 className="text-sm font-semibold text-gray-600 mb-3 flex items-center gap-2">
                词表（Glossary）
                <span className="text-xs font-normal text-gray-400">{detail.glossary.length} 项</span>
              </h3>

              <div className="bg-white border border-gray-200 rounded-xl overflow-hidden mb-3">
                {detail.glossary.length === 0 && (
                  <p className="text-sm text-gray-400 px-4 py-3">暂无词表项</p>
                )}
                {detail.glossary.map((e) => (
                  <div key={e.id} className="flex items-center gap-3 px-4 py-2.5 border-b border-gray-50 last:border-0 hover:bg-gray-50 group">
                    <span className="font-mono text-sm text-blue-700 min-w-[8rem]">{e.sourceTerm}</span>
                    <span className="text-gray-400">→</span>
                    <span className="font-mono text-sm text-green-700 flex-1">{e.targetTerm}</span>
                    {e.domain && <span className="text-xs text-gray-400 px-1.5 py-0.5 bg-gray-100 rounded">{e.domain}</span>}
                    <span className={`text-xs px-1.5 py-0.5 rounded ${e.origin === 'extracted' ? 'bg-purple-50 text-purple-600' : 'bg-blue-50 text-blue-600'}`}>
                      {e.origin === 'extracted' ? '提炼' : '手动'}
                    </span>
                    <button
                      onClick={() => delEntry.mutate(e.id)}
                      className="text-gray-300 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity ml-1"
                    >✕</button>
                  </div>
                ))}
              </div>

              <div className="flex gap-2">
                <input value={newSrcTerm} onChange={(e) => setNewSrcTerm(e.target.value)}
                  placeholder="原文术语" className="flex-1 border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300" />
                <input value={newTgtTerm} onChange={(e) => setNewTgtTerm(e.target.value)}
                  placeholder="偏好译文" className="flex-1 border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300" />
                <input value={newDomain} onChange={(e) => setNewDomain(e.target.value)}
                  placeholder="领域(可选)" className="w-24 border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none" />
                <button
                  onClick={() => {
                    if (!newSrcTerm || !newTgtTerm) return
                    addEntry.mutate({ sourceTerm: newSrcTerm, targetTerm: newTgtTerm, domain: newDomain || undefined })
                    setNewSrcTerm(''); setNewTgtTerm(''); setNewDomain('')
                  }}
                  className="px-4 py-1.5 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
                >
                  添加
                </button>
              </div>
            </section>

            {/* 翻译习惯 */}
            <section>
              <h3 className="text-sm font-semibold text-gray-600 mb-3 flex items-center gap-2">
                翻译习惯（Habit Rules）
                <span className="text-xs font-normal text-gray-400">{detail.habits.length} 条</span>
              </h3>

              <div className="bg-white border border-gray-200 rounded-xl overflow-hidden mb-3">
                {detail.habits.length === 0 && (
                  <p className="text-sm text-gray-400 px-4 py-3">暂无习惯规则</p>
                )}
                {detail.habits.map((h) => (
                  <div key={h.id} className="flex items-start gap-3 px-4 py-2.5 border-b border-gray-50 last:border-0 hover:bg-gray-50 group">
                    <span className="text-sm text-gray-700 flex-1">{h.description}</span>
                    <span className={`text-xs px-1.5 py-0.5 rounded shrink-0 ${h.origin === 'extracted' ? 'bg-purple-50 text-purple-600' : 'bg-blue-50 text-blue-600'}`}>
                      {h.origin === 'extracted' ? `提炼 ${Math.round(h.confidence * 100)}%` : '手动'}
                    </span>
                    <button
                      onClick={() => delHabit.mutate(h.id)}
                      className="text-gray-300 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity"
                    >✕</button>
                  </div>
                ))}
              </div>

              <div className="flex gap-2">
                <input value={newHabit} onChange={(e) => setNewHabit(e.target.value)}
                  placeholder="描述翻译习惯，如：技术术语保持英文原样" className="flex-1 border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300" />
                <button
                  onClick={() => {
                    if (!newHabit.trim()) return
                    addHabit.mutate({ description: newHabit.trim() })
                    setNewHabit('')
                  }}
                  className="px-4 py-1.5 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
                >
                  添加
                </button>
              </div>
            </section>
          </div>
        )}
      </div>
    </div>
  )
}
