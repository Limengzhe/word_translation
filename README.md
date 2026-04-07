# AI 翻译智能体

基于 FastAPI + React + TypeScript 的全栈 AI 翻译审校工具，支持：

- **流式翻译**：逐句 SSE 推送，实时显示翻译进度
- **Cursor 风格 Diff**：修改前/后对比，字符级高亮（删除红色、新增绿色）
- **Accept / Reject**：一键接受或拒绝每句修改
- **原文可编辑**：编辑原文后行变红，点击"同步翻译"变橙并流式重译
- **划选高亮对应**：在原文/译文划选，另一侧按比例高亮对应范围
- **Skills 系统**：词表（Glossary）+ 翻译习惯（Habit Rules），翻译前自动注入 prompt；支持从人工修改记录中 LLM 提炼习惯

---

## 目录结构

```
word/
├── backend/                  # FastAPI 后端
│   ├── requirements.txt
│   └── app/
│       ├── main.py           # FastAPI 入口
│       ├── core/             # 配置、错误
│       ├── db/               # SQLite session
│       ├── models/           # SQLModel ORM（document.py / skill.py）
│       ├── schemas/          # Pydantic DTO（document.py / skill.py）
│       ├── providers/        # LLM Provider 抽象（base / openai）
│       ├── services/         # 业务逻辑（segmentation / translation / revision / skill / prompt_builder）
│       └── api/              # FastAPI 路由（documents / segments / revisions / skills）
│
├── frontend/                 # React + TypeScript 前端
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── main.tsx / App.tsx
│       ├── types/contract.ts          # 前后端共享 DTO 类型
│       ├── lib/api/                   # API client（fetch / SSE）
│       ├── lib/diff/                  # diff-match-patch 封装
│       ├── lib/selection/             # DOM selection → offset 映射
│       ├── features/document/hooks.ts # TanStack Query 封装
│       ├── features/skills/hooks.ts
│       ├── components/                # SegmentList / SegmentRow / DiffView / …
│       └── pages/                     # HomePage / DocumentEditorPage / SkillsPage
│
└── .env                      # 环境变量（OPENAI_API_KEY 等）
```

---

## 快速启动

### 1. 配置环境变量

在项目根目录创建或编辑 `.env`：

```
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
OPENAI_BASE_URL=https://api.openai.com/v1
DEFAULT_MODEL=gpt-4.1-mini
```

### 2. 启动后端

```bash
cd backend
pip install -r requirements.txt
# Windows PowerShell
$env:PYTHONPATH="."
uvicorn app.main:app --reload --port 8000
```

或 Linux/macOS：

```bash
cd backend
pip install -r requirements.txt
PYTHONPATH=. uvicorn app.main:app --reload --port 8000
```

API 文档：http://localhost:8000/docs

### 3. 启动前端

```bash
cd frontend
npm install
npm run dev
```

访问：http://localhost:5173

---

## 核心流程

```
创建文档 → 自动切句 → POST /api/documents
开始翻译 → 流式 SSE   → POST /api/documents/{id}/translate/stream
编辑原文 → 行变红      → PATCH /api/segments/{id}/source
同步翻译 → 行变橙+SSE → POST  /api/segments/{id}/sync   → 产生 pending revision
接受修改 → POST        → PATCH /api/revisions/{id}  (action: accept)
拒绝修改              → PATCH /api/revisions/{id}  (action: reject)
```

## Skills 流程

```
手动添加词表/习惯 → /skills 页面
翻译时自动注入   → prompt_builder 在 system prompt 末尾拼接词表+习惯
从编辑记录提炼   → POST /api/skillsets/{id}/extract（LLM 分析 EditRecord）
```
