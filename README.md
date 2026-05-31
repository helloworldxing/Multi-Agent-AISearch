# Multi-Agent AI Research Assistant

本地优先的多 Agent 研究助手：LangGraph 工作流 + RAG + 任务审批流。前后端分离：FastAPI + React 18 + Vite + Tailwind + Lucide。

## 功能

- 注册 / 登录（SQLite + JWT）
- 用户面板：默认收件邮箱、深色 / 浅色主题切换
- 研究流程：意图判定 → AI 拆解步骤 → **用户审批面板（可改/增/删/排序）** → 并行检索 → 流式生成 → 自动落库
- 历史记录列表与详情查看（react-markdown 渲染）

## 目录结构

```
app/                后端：FastAPI + LangGraph
  api.py            REST + SSE 入口
  auth.py           JWT + bcrypt
  db.py             SQLite 初始化（users / histories）
  agents/ graph/ ...
frontend/           前端：Vite + React 18 + TS + Tailwind + Lucide
  src/
    contexts/       AuthContext, ThemeContext
    hooks/          useResearch（审批流状态机）
    components/     Header / ApprovalModal / SubtaskGrid / MarkdownView ...
    pages/          Login / Register / Research / History / Profile
data/               报告产物 + SQLite + JWT secret
web/                旧版单文件 UI（保留作为兜底）
```

## 开发

后端：

```bash
.venv/Scripts/python.exe -m uvicorn app.api:app --reload
# 监听 http://127.0.0.1:8000
```

前端（独立 dev server，自动代理 `/api` 到后端）：

```bash
cd frontend
npm install
npm run dev
# 访问 http://127.0.0.1:5173
```

## 生产合并部署

构建前端产物，FastAPI 会自动挂载 `frontend/dist`：

```bash
cd frontend && npm run build
cd .. && .venv/Scripts/python.exe -m uvicorn app.api:app --port 8000
# 访问 http://127.0.0.1:8000
```

未构建时回退到 `web/index.html` 旧版页面。

## 环境变量

`.env`（项目根）：

```
DEEPSEEK_API_KEY=...
TAVILY_API_KEY=...
APP_JWT_SECRET=（可选，未提供时自动生成并写入 data/.jwt_secret）
SMTP_HOST / SMTP_USER / SMTP_PASS / SMTP_FROM   # 邮件功能用
```

## 关键 API

| 方法 | 路径 | 鉴权 | 说明 |
|------|------|------|------|
| POST | `/api/auth/register` | - | 注册返回 token |
| POST | `/api/auth/login`    | - | 登录返回 token |
| GET  | `/api/auth/me`       | Bearer | 当前用户信息 |
| PATCH| `/api/auth/profile`  | Bearer | 更新默认邮箱 |
| GET  | `/api/research/plan` | Bearer | 仅做意图判定 + 子问题拆解 |
| GET  | `/api/research/stream` | `?token=...` | SSE 执行（审批后由前端带上 intent + subqueries） |
| GET  | `/api/history`       | Bearer | 列出最近 200 条记录 |
| GET  | `/api/history/{id}`  | Bearer | 历史详情（含完整文档） |
| DELETE | `/api/history/{id}` | Bearer | 删除历史 |
