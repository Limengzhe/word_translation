// ── Settings ──────────────────────────────────────────────────────────────────
export interface DocumentSettings {
  provider: 'openai' | 'mock'
  model: string
  temperature: number
  stylePreset?: string
  glossaryId?: string
}

// ── Document ──────────────────────────────────────────────────────────────────
export interface DocumentDto {
  id: string
  sourceLang: string
  targetLang: string
  createdAt: string
  updatedAt: string
  settings: DocumentSettings
  /** Mammoth 输出的完整 HTML（含表格/标题等原始排版） */
  fullSourceHtml?: string
  /** LLM 翻译后的完整 HTML */
  fullTranslatedHtml?: string
}

// ── Segment ───────────────────────────────────────────────────────────────────
export type TargetStatus = 'machine' | 'accepted'
export type SourceStatus = 'clean' | 'source_edited' | 'syncing'
export type ParaType = 'h1' | 'h2' | 'h3' | 'h4' | 'h5' | 'h6' | 'p' | 'li' | 'blockquote' | 'pre'

export interface SegmentDto {
  id: string
  documentId: string
  index: number
  paraType: ParaType
  /** Mammoth 原始 HTML 片段（服务器存储并原样返回） */
  sourceHtml?: string
  sourceText: string
  syncedSourceText: string
  currentText: string
  targetStatus: TargetStatus
  sourceStatus: SourceStatus
  pendingRevisionId?: string
}

// ── Diff ──────────────────────────────────────────────────────────────────────
export type DiffOpType = 'equal' | 'insert' | 'delete'

export interface DiffOp {
  type: DiffOpType
  text: string
}

// ── Revision ──────────────────────────────────────────────────────────────────
export type RevisionProposer = 'user' | 'model'
export type RevisionState = 'pending' | 'accepted' | 'rejected'

export interface SegmentRevisionDto {
  id: string
  segmentId: string
  baseText: string
  proposedText: string
  proposer: RevisionProposer
  state: RevisionState
  createdAt: string
  diff?: DiffOp[]
}

// ── Skills ────────────────────────────────────────────────────────────────────
export type SkillScope = 'universal' | 'lang_pair'
export type OriginType = 'manual' | 'extracted'

export interface SkillSetDto {
  id: string
  name: string
  scope: SkillScope
  sourceLang?: string
  targetLang?: string
  createdAt: string
  updatedAt: string
}

export interface GlossaryEntryDto {
  id: string
  skillSetId: string
  sourceTerm: string
  targetTerm: string
  domain?: string
  note?: string
  origin: OriginType
  createdAt: string
}

export interface HabitRuleDto {
  id: string
  skillSetId: string
  description: string
  example?: { source: string; preferred: string; avoided?: string }
  origin: OriginType
  confidence: number
  createdAt: string
}

export interface EditRecordDto {
  id: string
  documentId: string
  segmentId: string
  sourceLang: string
  targetLang: string
  sourceText: string
  baseText: string
  acceptedText: string
  proposer: RevisionProposer
  createdAt: string
  extracted: boolean
}

export interface SkillSetDetailDto {
  skillSet: SkillSetDto
  glossary: GlossaryEntryDto[]
  habits: HabitRuleDto[]
}

// ── API Request / Response ────────────────────────────────────────────────────
export interface ParagraphIn {
  text: string
  paraType: ParaType
  /** Mammoth 生成的原始 HTML 片段，含加粗/斜体/下划线等内联格式 */
  sourceHtml?: string
}

export interface CreateDocumentRequest {
  sourceLang: string
  targetLang: string
  /** 优先使用结构化段落（来自 Mammoth 解析） */
  paragraphs?: ParagraphIn[]
  /** fallback：纯文本 */
  sourceText?: string
  /** Mammoth 输出的完整 HTML（含表格/标题等原始排版） */
  fullSourceHtml?: string
  settings: DocumentSettings
}

export interface CreateDocumentResponse {
  document: DocumentDto
  segments: SegmentDto[]
}

export interface GetDocumentResponse {
  document: DocumentDto
  segments: SegmentDto[]
}

export interface PatchSourceRequest {
  sourceText: string
}

export interface PatchTargetRequest {
  userEditedText: string
}

export interface RewriteRequest {
  instruction: string
  stylePreset?: string
}

export interface ApplyRevisionRequest {
  action: 'accept' | 'reject'
}

export interface ApplyRevisionResponse {
  segment: SegmentDto
  revision: SegmentRevisionDto
}

export interface ExtractResult {
  extractedCount: number
  addedGlossary: number
  addedHabits: number
}
