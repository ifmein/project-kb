---
name: project-kb
description: 管理本地项目知识库（pkb CLI）。当用户提到项目进度、任务、备忘录、决策记录、全文搜索历史讨论，或者任何"记录一下"、"查一下之前"、"项目状态"、"有什么任务"等场景时使用此 skill。pkb 是本地 SQLite + FTS5 工具，支持中文和拼音搜索，所有命令加 --json 输出可直接 json.loads()。即使用户只是随口说"记录一个决定"或"看看 xxx 项目有什么进展"，也应触发此 skill。
---

# pkb — Project Knowledge Base

本地 CLI 工具，管理项目、任务、备忘录，支持中文和拼音全文搜索。

> **环境变量**：`PKB_DB_PATH`（默认 `~/.config/project-kb/pkb.db`）、`PKB_SIMPLE_EXT`（libsimple 路径，不带扩展名）。首次使用先运行 `pkb init`。

---

## 基本原则

- **agent 调用一律加 `--json`**，返回值可直接 `json.loads()`
- 项目用 `id`（`proj_*`）或 `name` 引用；任务、备忘只能用 `id`
- 拼音搜索用**空格分隔全拼**（如 `jue ce` 匹配"决策"），不支持声母缩写（`jc` 无效）
- 失败时 `--json` 返回 `{"success": false, "error": "..."}`，exit code 1

---

## 初始化

```bash
pkb init      # 首次：创建 ~/.config/project-kb/，建表，加载 libsimple
pkb status    # 查看 DB 路径、扩展状态、各表记录数
```

---

## 项目 `pkb project`

```bash
pkb project list [--status active|paused|completed|archived] [--json]
pkb project add --name "名称" [--desc "描述"] [--status active] [--repo "url"] [--path "/本地路径"] [--tech "Python,SQLite"] [--json]
pkb project show <id|name> [--json]          # 详情 + 任务统计
pkb project update <id|name> [--name "新名"] [--desc "..."] [--status paused] [--repo "url"] [--path "..."] [--tech "..."] [--json]
pkb project delete <id|name> [--yes] [--json]  # 级联删除 tasks / notes
```

**`project list --json` 输出**：

```json
{
  "success": true,
  "projects": [
    { "id": "proj_XXX", "name": "项目名", "description": "...", "status": "active",
      "repo_url": "", "local_path": "/路径", "tech_stack": "", "created_at": "2026-04-23", "updated_at": "2026-04-23" }
  ],
  "count": 1
}
```

**`project show --json` 输出**：

```json
{
  "success": true,
  "project": { "id": "proj_XXX", "name": "...", "status": "active" },
  "task_stats": { "todo": 3, "in_progress": 1, "done": 5 }
}
```

---

## 任务 `pkb task`

```bash
pkb task list --project <id|name> [--status todo|in_progress|done|cancelled] [--priority P0|P1|P2|P3] [--json]
pkb task add --project <id|name> --title "标题" [--desc "描述"] [--priority P2] [--assignee "名字"] [--due "2026-05-01"] [--json]
pkb task show <task_id> [--json]
pkb task update <task_id> [--title "..."] [--desc "..."] [--status in_progress] [--priority P1] [--assignee "..."] [--due "..."] [--json]
pkb task done <task_id> [--json]    # 快捷标记完成
pkb task delete <task_id> [--json]
```

**priority**：`P0` 紧急 / `P1` / `P2` 默认 / `P3` 低优

**`task list --json` 输出**：

```json
{
  "success": true,
  "tasks": [
    { "id": "task_XXX", "project_id": "proj_XXX", "title": "标题", "description": "",
      "status": "todo", "priority": "P1", "assignee": "", "due_date": "",
      "created_at": "2026-04-23", "updated_at": "2026-04-23" }
  ],
  "count": 1
}
```

---

## 备忘录 `pkb note`

```bash
pkb note add "内容" [--project <id|name>] [--tags "决策,会议"] [--json]   # project 可选
pkb note list [--project <id|name>] [--limit 20] [--json]
pkb note show <note_id> [--json]
pkb note delete <note_id> [--json]
```

**`note list --json` 输出**：

```json
{
  "success": true,
  "notes": [
    { "id": "note_XXX", "project_id": "proj_XXX", "content": "内容", "tags": "决策,会议", "created_at": "2026-04-23" }
  ],
  "count": 1
}
```

---

## 搜索 `pkb search`

```bash
pkb search "关键词" [--json]
pkb search "jue ce" [--json]                          # 拼音全拼，空格分隔
pkb search "关键词" --project <id|name> [--json]
pkb search "关键词" --type project|task|note [--json]
```

> **注意**：关键词中含连字符（如 `my-term`）时 FTS5 会解析为 NOT，改用 `myterm` 或加引号。

**`search --json` 输出**（按相关性降序，`results[0]` 最相关，不暴露 rank 值）：

```json
{
  "success": true,
  "query": "ntfy",
  "results": [
    { "type": "note", "id": "note_XXX", "project": "项目名", "content": "...", "tags": "决策", "created_at": "2026-04-23" },
    { "type": "task", "id": "task_XXX", "project": "项目名", "title": "...", "status": "in_progress", "priority": "P1", "created_at": "2026-04-23" },
    { "type": "project", "id": "proj_XXX", "name": "项目名", "description": "...", "status": "active", "created_at": "2026-04-23" }
  ],
  "count": 3
}
```

---

## Agent 调用模式

### 查询项目进度

```bash
pkb project show <name> --json     # task_stats 含各状态计数
pkb task list --project <name> --status todo --json
```

### 记录决策 / 会议纪要

```bash
pkb note add "决定采用 XXX 方案，原因是..." --project <name> --tags "决策" --json
```

### 查找历史讨论

```bash
pkb search "关键词" --json
pkb search "关键词" --project <name> --type note --json
```

### 注入上下文到 system prompt

```bash
pkb project list --json    # 获取所有项目，生成摘要写入 system prompt
```

---

## 常见错误

| 错误信息 | 处理方式 |
|---|---|
| `no such tokenizer: simple` | 运行 `pkb init` 初始化扩展 |
| `Project not found` | 用 `pkb project list` 确认名称 |
| FTS5 连字符问题 | 关键词去掉 `-` 或改用引号包裹 |
