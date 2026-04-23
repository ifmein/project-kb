# Project Knowledge Base (pkb) - 产品需求文档

## 背景

从 session_search 联想到：Hermes 的 session 系统通过 SQLite + FTS5 实现了对话历史的存储和检索，配合 LLM 总结，让 agent 能"回忆"起之前的对话。

项目管理需要同样的能力——存储项目信息、任务、决策记录，并支持快速检索。当 agent 被问到项目相关问题时，能自动查询并返回结构化信息。

## 定位

CLI 工具，SQLite 存储，作为 agent 的项目知识库后端。

- 不是给真人用的 TUI/Web 应用
- 主要通过 agent 调用，也可以 CLI 直接用
- 参考 session_search 的设计模式：存储 + 搜索 + LLM 总结

## 数据模型

### projects

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PK | 格式: `proj_<nanoid>` |
| name | TEXT | 项目名，唯一 |
| description | TEXT | 项目描述 |
| status | TEXT | active / paused / completed / archived |
| repo_url | TEXT | 仓库地址（Gitea/GitHub） |
| tech_stack | TEXT | 技术栈，逗号分隔 |
| created_at | REAL | Unix timestamp |
| updated_at | REAL | Unix timestamp |

### tasks

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PK | 格式: `task_<nanoid>` |
| project_id | TEXT FK | 关联项目 |
| title | TEXT | 任务标题 |
| description | TEXT | 详细描述 |
| status | TEXT | todo / in_progress / done / cancelled |
| priority | TEXT | P0 / P1 / P2 / P3 |
| assignee | TEXT | 负责人 |
| due_date | TEXT | 截止日期 (ISO 8601) |
| created_at | REAL | Unix timestamp |
| updated_at | REAL | Unix timestamp |

### notes

| 字段 | 类型 | 说明 |
|------|------|------|
| id | TEXT PK | 格式: `note_<nanoid>` |
| project_id | TEXT FK | 关联项目（可为空 = 全局备忘） |
| content | TEXT | 备忘内容 |
| tags | TEXT | 标签，逗号分隔 |
| created_at | REAL | Unix timestamp |

### FTS5 虚拟表

参考 session_search，使用 **external content + trigger** 方案自动同步：

```sql
-- 外部内容表，指向主表
CREATE VIRTUAL TABLE notes_fts USING fts5(
    content,
    content=notes,
    content_rowid=rowid
);

CREATE VIRTUAL TABLE tasks_fts USING fts5(
    title, description,
    content=tasks,
    content_rowid=rowid
);

-- 三个 trigger 自动同步（INSERT / DELETE / UPDATE）
-- 与 session_search 的 messages_fts 设计一致
-- 见 db.py 中的建表语句
```

**为什么用 trigger 而不是手动写入**：
- 一致性由数据库保证，不会漏写
- 代码里只需 INSERT INTO notes，FTS 自动跟上
- session_search 验证过这条路

## CLI 接口

### 项目管理

```bash
pkb project list [--status active]           # 列出项目
pkb project add --name "xxx" --desc "..."    # 新建项目
pkb project show <id|name>                   # 项目详情（含统计）
pkb project update <id> --status paused      # 更新字段
pkb project delete <id>                      # 删除（级联删除 tasks/notes）
```

### 任务管理

```bash
pkb task list --project <id> [--status todo] [--priority P1]  # 任务列表
pkb task add --project <id> --title "..." [--priority P1]     # 新建任务
pkb task show <id>                                            # 任务详情
pkb task update <id> --status done                            # 更新状态
pkb task done <id>                                            # 快捷: 标记完成
pkb task delete <id>                                          # 删除
```

### 备忘录

```bash
pkb note add --project <id> "内容" [--tags "决策,会议"]       # 添加备忘
pkb note list --project <id> [--limit 10]                      # 列出备忘
pkb note show <id>                                             # 查看详情
pkb note delete <id>                                           # 删除
```

### 搜索（参考 session_search）

```bash
pkb search "关键词"                       # 全局 FTS5 搜索
pkb search "关键词" --project <id>        # 限定项目
pkb search "关键词" --type task           # 限定类型 (task/note/project)
```

**搜索返回格式**：

参考 session_search：**不返回 relevance 分数**，FTS5 的 rank 是负数（越小越相关），暴露出去会让 agent 困惑。
搜索结果按相关性排序，results[0] 最相关，顺序本身即暗示相关性。

```json
{
  "success": true,
  "query": "ntfy",
  "results": [
    {
      "type": "note",
      "id": "note_xxx",
      "project": "hermes-workspace",
      "content": "...",
      "created_at": "2026-04-21"
    }
  ],
  "count": 1
}
```

### Agent 接口（JSON 输出）

所有命令支持 `--json` 输出，方便 agent 解析：

```bash
pkb search "ntfy" --json
pkb project list --json
pkb task list --project hermes-workspace --json
```

## 参考 session_search 的设计模式

| session_search | pkb 对应 |
|----------------|----------|
| SQLite + FTS5 | SQLite + FTS5 (notes_fts, tasks_fts) |
| external content + trigger 自动同步 | 同上，trigger 保证 FTS 与主表一致 |
| 无 query → 返回最近 session | 无 search term → 返回最近记录 |
| 有 query → FTS5 + LLM 总结 | 有 search term → FTS5 返回结构化结果 |
| 不返回 relevance 分数，靠排序暗示 | 同上，不暴露 FTS5 rank 负数值 |
| _truncate_around_matches 截取上下文 | 按相关性排序，返回完整内容（项目数据量小，不需要截取） |
| _resolve_to_parent 去重 | 按 project 聚合 |
| 并发控制 (semaphore) | 不需要（本地 SQLite，足够快） |
| LLM 总结 | 可选：`pkb summarize --project <id>` 生成项目概览 |

## 与 Agent 集成

### 自动触发

当用户问项目相关内容时，agent 自动调用：

```
用户: "nous-portal-kit 进度怎么样了？"
agent: pkb task list --project nous-portal-kit --json
       → 返回任务列表，整理后回复
```

### 上下文注入

在 system prompt 中注入项目摘要（类似 memory 注入）：

```
## 项目知识库
- nous-portal-kit: OAuth 客户端，进度 60%，当前在做 token 刷新
- mteam-kit: M-Team API 封装，已完成
```

### Bark 推通知

任务状态变更时推送：

```bash
curl "$BARK_HOST/pkb更新/任务xxx已标记完成"
```

## 技术实现

- **Python 3.12+** + **Click** (CLI)
- **SQLite** + FTS5
- **nanoid** 生成 ID
- **uv** 管理依赖，inline dependencies
- **pytest** 测试
- **ruff** lint
- Flat 布局: `main.py` + `db.py` + `cli.py`

## 目录结构

```
project-kb/
├── PRD.md          # 本文档
├── pyproject.toml
├── main.py         # 入口
├── cli.py          # Click CLI 定义
├── db.py           # SQLite 操作 + FTS5
├── models.py       # 数据模型 (dataclass)
├── search.py       # 搜索逻辑
└── tests/
    ├── test_db.py
    ├── test_cli.py
    └── test_search.py
```

## 验收标准

1. `pkb project add --name test --desc "测试项目"` 成功创建
2. `pkb task add --project test --title "做点什么"` 关联到项目
3. `pkb note add --project test "今天讨论了xxx"` 支持
4. `pkb search "xxx"` FTS5 搜索返回结果
5. `pkb project show test` 显示项目 + 任务统计
6. 所有命令 `--json` 输出格式正确
7. pytest 测试通过
