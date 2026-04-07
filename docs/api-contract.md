# API契约（MVP）：Documents / Segments / Revisions + SSE进度

> 目标：前后端严格对齐协议与错误处理；MVP采用REST + 可选SSE。

## 1. 通用约定
### 1.1 Base URL
- 前端通过 `/api` 访问后端（本地开发可用反向代理或CORS）。

### 1.2 通用响应包装（MVP建议但不强制）
- 成功：直接返回资源JSON
- 失败：返回统一错误结构：
```json
{
  "error": {
    "code": "REVISION_NOT_PENDING",
    "message": "Revision is not pending",
    "details": {
      "revisionId": "rev_..."
    }
  }
}
```

### 1.3 错误码（枚举）
- `VALIDATION_ERROR`：入参校验失败（422）
- `NOT_FOUND`：资源不存在（404）
- `CONFLICT`：并发冲突（409）
- `REVISION_NOT_PENDING`：revision 已非pending（409）
- `SEGMENT_HAS_PENDING_REVISION`：segment已存在pending（409）
- `SEGMENT_TOO_LONG`：句子过长（413或422）
- `PROVIDER_ERROR`：模型provider失败（502/503）
- `RATE_LIMITED`：限流（429）

### 1.4 幂等与并发（MVP）
- **同一Segment最多1条pending revision**。
- `PATCH /api/revisions/{revisionId}` 仅当 `state==pending` 才可操作，否则返回 `REVISION_NOT_PENDING`。

## 2. 数据类型（DTO）
> 这里用“伪TypeScript”表达字段；后端以Pydantic实现同构字段名。

### 2.1 Document
```ts
type Document = {
  id: string
  sourceLang: string
  targetLang: string
  createdAt: string
  updatedAt: string
  settings: {
    provider: "openai" | "mock"
    model: string
    temperature: number
    stylePreset?: string
    glossaryId?: string
  }
}
```

### 2.2 Segment
```ts
type SegmentStatus = "machine" | "accepted"

type Segment = {
  id: string
  documentId: string
  index: number
  sourceText: string
  currentText: string
  status: SegmentStatus
  pendingRevisionId?: string
}
```

### 2.3 SegmentRevision
```ts
type RevisionProposer = "user" | "model"
type RevisionState = "pending" | "accepted" | "rejected"

type DiffOp = { type: "equal" | "insert" | "delete"; text: string }

type SegmentRevision = {
  id: string
  segmentId: string
  baseText: string
  proposedText: string
  proposer: RevisionProposer
  state: RevisionState
  createdAt: string
  diff?: DiffOp[]
}
```

## 3. REST API
### 3.1 创建Document并切句
**POST** `/api/documents`

Request:
```json
{
  "sourceLang": "en",
  "targetLang": "zh",
  "sourceText": "Hello world. ...",
  "settings": {
    "provider": "openai",
    "model": "gpt-4.1-mini",
    "temperature": 0.2,
    "stylePreset": "tech_doc"
  }
}
```

Response:
```json
{
  "document": { "id": "doc_...", "sourceLang": "en", "targetLang": "zh", "createdAt": "...", "updatedAt": "...", "settings": { "provider": "openai", "model": "gpt-4.1-mini", "temperature": 0.2, "stylePreset": "tech_doc" } },
  "segments": [
    { "id": "seg_1", "documentId": "doc_...", "index": 0, "sourceText": "Hello world.", "currentText": "", "status": "machine" }
  ]
}
```

### 3.2 流式翻译（SSE，逐句输出）
**POST** `/api/documents/{docId}/translate/stream`

> 使用 Server-Sent Events（SSE）逐句推送翻译结果，类似 Cursor 代码生成体验。
> 前端建立 EventSource 连接后，后端按顺序逐句调用模型并 flush 每句结果。

Request body（可选参数）：
```json
{ "stylePreset": "tech_doc" }
```

SSE 事件流（每句翻译完毕即推送）：

```
event: started
data: {"docId":"doc_...","total":5}

event: segment
data: {"segmentId":"seg_1","index":0,"currentText":"你好，世界。","status":"machine"}

event: segment
data: {"segmentId":"seg_2","index":1,"currentText":"这是第二句。","status":"machine"}

event: completed
data: {"docId":"doc_...","translated":5}
```

错误事件：
```
event: error
data: {"code":"PROVIDER_ERROR","message":"OpenAI timeout","segmentId":"seg_3"}
```

> 注意：`error` 事件不中断流，前端收到后继续等待后续句子，并在该句显示错误状态；
> 若整体失败则推送 `event: fatal` 后关闭连接。

### 3.3 获取文档与segments（含pending标识）
**GET** `/api/documents/{docId}`

Response:
```json
{
  "document": { "id": "doc_..." },
  "segments": [
    { "id": "seg_1", "documentId": "doc_...", "index": 0, "sourceText": "Hello world.", "currentText": "你好，世界。", "status": "machine", "pendingRevisionId": "rev_1" }
  ]
}
```

### 3.4 用户编辑某句（创建pending revision）
**PATCH** `/api/segments/{segmentId}`

Request:
```json
{ "userEditedText": "你好，世界！" }
```

Response:
```json
{
  "revision": {
    "id": "rev_1",
    "segmentId": "seg_1",
    "baseText": "你好，世界。",
    "proposedText": "你好，世界！",
    "proposer": "user",
    "state": "pending",
    "createdAt": "...",
    "diff": [
      { "type": "equal", "text": "你好，世界" },
      { "type": "delete", "text": "。" },
      { "type": "insert", "text": "！" }
    ]
  }
}
```

409:
- `SEGMENT_HAS_PENDING_REVISION`

### 3.5 模型改写某句（创建pending revision）
**POST** `/api/segments/{segmentId}/rewrite`

Request:
```json
{
  "instruction": "更正式一些，适合技术文档",
  "stylePreset": "tech_doc"
}
```

Response: 同3.4（proposer=model）

### 3.6 Accept/Reject revision（应用或丢弃）
**PATCH** `/api/revisions/{revisionId}`

Request:
```json
{ "action": "accept" }
```

Response:
```json
{
  "segment": { "id": "seg_1", "currentText": "你好，世界！", "status": "accepted" },
  "revision": { "id": "rev_1", "state": "accepted" }
}
```

409:
- `REVISION_NOT_PENDING`

## 4. 流式翻译 SSE 规格（核心机制）
### 4.1 事件类型（枚举）
- `started`：翻译任务启动（携带 total 句数）
- `segment`：单句翻译完成（主要数据事件，逐句推送）
- `completed`：全部完成
- `error`：单句失败（非致命，继续）
- `fatal`：整体失败（断开连接）

### 4.2 `segment` 事件字段
```ts
type SegmentSseEvent = {
  segmentId: string;
  index: number;
  currentText: string;
  status: 'machine';
};
```

### 4.3 前端消费策略
- 建立 `EventSource` 连接（或用 `fetch` + `ReadableStream` 处理 POST 场景）
- 收到 `segment` 事件时：
  - 立即更新对应句子的 `currentText`（乐观渲染）
  - 对应行显示"正在翻译…"骨架直到事件到达
- 收到 `completed` 后关闭连接、清空进度状态
- 收到 `error` 后在该句显示重试按钮，不阻断其余句子
- 收到 `fatal` 后全局提示，保留已翻译部分
- **断线重连**：`EventSource` 原生支持重连，后端需支持 `Last-Event-ID`（可选增强）

### 4.4 单句重译是否流式（可选增强，非MVP）
- MVP：`POST /api/segments/{segmentId}/rewrite` 仍为同步返回（单句快，无需流式）
- M4增强：若重译耗时长，可对 rewrite 也引入 SSE token 流

