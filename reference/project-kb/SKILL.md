---
name: project-kb
description: |
  project knowledge base CLI tool, built with Python, SQLite, and FTS5.
  It supports Chinese tokenization and pinyin search (via libsimple tokenizer).
  All commands can output JSON (`--json`), making it easy for agents to call.
  When users mention keywords like "我的项目", "pkb", etc., prioritize information related to this tool.
---

# pkb — Project Knowledge Base CLI

本地 CLI 工具，管理项目、任务、备忘录，支持中文和拼音全文搜索。
**运行方式：`uv run pkb <命令>`**（需设置 `PKB_SIMPLE_EXT` 或先运行 `pkb init`）

---

## 基本原则

- 所有命令加 `--json` 后返回可 `json.loads()` 的结构化输出，agent 调用优先使用 `--json`
- 项目可用 `id`（`proj_*`）或 `name` 引用；任务只能用 `id`（`task_*`）；备忘只能用 `id`（`note_*`）
- 搜索支持中文关键词和空格分隔的全拼（如 `jue ce` 匹配"决策"），不支持声母缩写（如 `jc`）

---

## 命令速查

### 初始化

```bash
uv run pkb init      # 首次：创建 ~/.config/project-kb/，复制 libsimple.dylib，建表
uv run pkb status    # 查看 DB 路径、扩展加载状态、各表记录数
```

---

### 项目 `pkb project`

```bash
# 列出所有项目
uv run pkb project list [--status active|paused|completed|archived] [--json]

# 新建项目
uv run pkb project add --name "项目名" [--desc "描述"] [--status active] [--repo "url"] [--tech "Python,SQLite"] [--json]

# 查看详情（含任务统计）
uv run pkb project show <id|name> [--json]

# 更新字段（只传需要修改的字段）
uv run pkb project update <id|name> [--name "新名"] [--desc "新描述"] [--status paused] [--repo "url"] [--tech "stack"] [--json]

# 删除（级联删除关联的 tasks 和 notes）
uv run pkb project delete <id|name> [--yes] [--json]
```

**`project list --json` 输出格式：**

```json
{
  "success": true,
  "projects": [
    {
      "id": "proj_XXX",
      "name": "项目名",
      "description": "描述",
      "status": "active",
      "repo_url": "",
      "tech_stack": "",
      "created_at": "2026-04-23",
      "updated_at": "2026-04-23"
    }
  ],
  "count": 1
}
```

**`project show --json` 输出格式：**

```json
{
  "success": true,
  "project": { "id": "proj_XXX", "name": "...", "status": "active", "...": "..." },
  "task_stats": { "todo": 3, "in_progress": 1, "done": 5 }
}
```

---

### 任务 `pkb task`

```bash
# 列出项目任务
uv run pkb task list --project <id|name> [--status todo|in_progress|done|cancelled] [--priority P0|P1|P2|P3] [--json]

# 新建任务
uv run pkb task add --project <id|name> --title "标题" [--desc "描述"] [--priority P2] [--assignee "名字"] [--due "2026-05-01"] [--json]

# 查看任务详情
uv run pkb task show <task_id> [--json]

# 更新任务（只传需要修改的字段）
uv run pkb task update <task_id> [--title "新标题"] [--desc "新描述"] [--status in_progress] [--priority P1] [--assignee "名字"] [--due "2026-05-01"] [--json]

# 快捷标记完成
uv run pkb task done <task_id> [--json]

# 删除任务
uv run pkb task delete <task_id> [--json]
```

**status 有效值：** `todo` / `in_progress` / `done` / `cancelled`
**priority 有效值：** `P0`（紧急）/ `P1` / `P2`（默认）/ `P3`（低优先级）

**`task list --json` 输出格式：**

```json
{
  "success": true,
  "tasks": [
    {
      "id": "task_XXX",
      "project_id": "proj_XXX",
      "title": "任务标题",
      "description": "",
      "status": "todo",
      "priority": "P1",
      "assignee": "",
      "due_date": "",
      "created_at": "2026-04-23",
      "updated_at": "2026-04-23"
    }
  ],
  "count": 1
}
```

---

### 备忘录 `pkb note`

```bash
# 添加备忘（project 可选，不传则为全局备忘）
uv run pkb note add "备忘内容" [--project <id|name>] [--tags "决策,会议"] [--json]

# 列出备忘
uv run pkb note list [--project <id|name>] [--limit 20] [--json]

# 查看单条备忘
uv run pkb note show <note_id> [--json]

# 删除备忘
uv run pkb note delete <note_id> [--json]
```

**`note list --json` 输出格式：**

```json
{
  "success": true,
  "notes": [
    {
      "id": "note_XXX",
      "project_id": "proj_XXX",
      "content": "备忘内容",
      "tags": "决策,会议",
      "created_at": "2026-04-23"
    }
  ],
  "count": 1
}
```

---

### 搜索 `pkb search`

```bash
# 全局搜索（覆盖 projects / tasks / notes）
uv run pkb search "关键词" [--json]

# 拼音搜索（空格分隔全拼，不支持声母缩写）
uv run pkb search "jue ce" [--json]   # 匹配含"决策"的内容

# 限定项目
uv run pkb search "关键词" --project <id|name> [--json]

# 限定类型
uv run pkb search "关键词" --type project|task|note [--json]
```

**搜索 `--json` 输出格式：**

```json
{
  "success": true,
  "query": "ntfy",
  "results": [
    {
      "type": "note",
      "id": "note_XXX",
      "project": "项目名",
      "content": "备忘内容",
      "tags": "决策",
      "created_at": "2026-04-23"
    },
    {
      "type": "task",
      "id": "task_XXX",
      "project": "项目名",
      "title": "任务标题",
      "status": "in_progress",
      "priority": "P1",
      "created_at": "2026-04-23"
    },
    {
      "type": "project",
      "id": "proj_XXX",
      "name": "项目名",
      "description": "项目描述",
      "status": "active",
      "created_at": "2026-04-23"
    }
  ],
  "count": 3
}
```

结果按相关性降序排列（`results[0]` 最相关），不暴露 FTS5 rank 值。

---

## Agent 调用模式

### 查询项目进度

```bash
uv run pkb task list --project <name> --json
uv run pkb project show <name> --json   # task_stats 含各状态计数
```

### 记录决策/会议纪要

```bash
uv run pkb note add "今天决定采用 XXX 方案，原因是..." --project <name> --tags "决策" --json
```

### 查找历史讨论

```bash
uv run pkb search "关键词" --json
uv run pkb search "关键词" --project <name> --type note --json
```

### 注入上下文到 system prompt

```bash
uv run pkb project list --json   # 获取所有项目列表，生成摘要后写入 system prompt
```

---

## 错误处理

所有命令在失败时：

- `--json` 模式：返回 `{"success": false, "error": "错误信息"}`，exit code 1
- 普通模式：打印红色错误信息，exit code 1

常见错误：

- `no such tokenizer: simple` → 运行 `pkb init` 初始化扩展
- `Project not found` → 检查项目名/id 是否正确，用 `pkb project list` 确认
- FTS5 搜索包含连字符（如 `my-term`）→ FTS5 把 `-` 解析为 NOT，改用 `myterm` 或加引号

---

## 环境变量

| 变量             | 说明                                                          |
| ---------------- | ------------------------------------------------------------- |
| `PKB_DB_PATH`    | 数据库路径，默认 `~/.config/project-kb/pkb.db`                |
| `PKB_SIMPLE_EXT` | libsimple 扩展路径（不带 `.dylib`），未设置时自动检测默认位置 |
