# Project Knowledge Base (pkb) - 产品需求文档

## 背景

从 session_search 联想到：Hermes 的 session 系统通过 SQLite + FTS5 实现了对话历史的存储和检索，配合 LLM 总结，让 agent 能"回忆"起之前的对话。

项目管理需要同样的能力——存储项目信息、任务、决策记录，并支持快速检索。当 agent 被问到项目相关问题时，能自动查询并返回结构化信息。

## 定位

CLI 工具，SQLite 存储，作为 agent 的项目知识库后端。

- 不是给真人用的 TUI/Web 应用
- 主要通过 agent 调用，也可以 CLI 直接用
- **仅在本机运行**，无需跨机部署
- 参考 session_search 的设计模式：存储 + 搜索 + LLM 总结

## 数据模型

### projects

| 字段        | 类型    | 说明                                   |
| ----------- | ------- | -------------------------------------- |
| id          | TEXT PK | 格式: `proj_<nanoid>`                  |
| name        | TEXT    | 项目名，唯一                           |
| description | TEXT    | 项目描述                               |
| status      | TEXT    | active / paused / completed / archived |
| repo_url    | TEXT    | 仓库地址（Gitea/GitHub）               |
| local_path  | TEXT    | 本地文件系统路径                       |
| tech_stack  | TEXT    | 技术栈，逗号分隔                       |
| created_at  | REAL    | Unix timestamp                         |
| updated_at  | REAL    | Unix timestamp                         |

### tasks

| 字段        | 类型    | 说明                                  |
| ----------- | ------- | ------------------------------------- |
| id          | TEXT PK | 格式: `task_<nanoid>`                 |
| project_id  | TEXT FK | 关联项目                              |
| title       | TEXT    | 任务标题                              |
| description | TEXT    | 详细描述                              |
| status      | TEXT    | todo / in_progress / done / cancelled |
| priority    | TEXT    | P0 / P1 / P2 / P3                     |
| assignee    | TEXT    | 负责人                                |
| due_date    | TEXT    | 截止日期 (ISO 8601)                   |
| created_at  | REAL    | Unix timestamp                        |
| updated_at  | REAL    | Unix timestamp                        |

### notes

| 字段       | 类型    | 说明                          |
| ---------- | ------- | ----------------------------- |
| id         | TEXT PK | 格式: `note_<nanoid>`         |
| project_id | TEXT FK | 关联项目（可为空 = 全局备忘） |
| content    | TEXT    | 备忘内容                      |
| tags       | TEXT    | 标签，逗号分隔                |
| created_at | REAL    | Unix timestamp                |

### FTS5 虚拟表

使用 **simple tokenizer**（外部 `.dylib` 扩展）+ **external content + trigger** 方案：

```sql
-- simple tokenizer 支持中文分词 + 拼音搜索
CREATE VIRTUAL TABLE projects_fts USING fts5(
    name, description,
    content=projects,
    content_rowid=rowid,
    tokenize='simple'
);

CREATE VIRTUAL TABLE notes_fts USING fts5(
    content,
    content=notes,
    content_rowid=rowid,
    tokenize='simple'
);

CREATE VIRTUAL TABLE tasks_fts USING fts5(
    title, description,
    content=tasks,
    content_rowid=rowid,
    tokenize='simple'
);

-- 三个 trigger 自动同步（INSERT / DELETE / UPDATE），与 session_search 一致
-- 见 db.py 中的完整建表语句
```

**为什么用 simple tokenizer 而不是内置 trigram**：

|              | trigram | simple                       |
| ------------ | ------- | ---------------------------- |
| 中文子串搜索 | ✅      | ✅                           |
| 拼音搜索     | ❌      | ✅（输入 `xm` 能匹配"项目"） |
| 索引体积     | 大 ~3x  | 正常                         |
| 部署         | 零依赖  | 需要 `libsimple.dylib`       |

本机专用，部署成本固定一次，拼音搜索对 agent 有实用价值（agent 有时输入拼音缩写），选 simple。

**为什么用 trigger 而不是手动写入**：

- 一致性由数据库保证，不会漏写
- 代码里只需 `INSERT INTO notes`，FTS 自动跟上
- session_search 验证过这条路

## 环境与配置

所有文件集中在 `~/.config/project-kb/`，方便 dotfiles 同步工具（如 chezmoi / rsync）统一管理：

```
~/.config/project-kb/
├── pkb.db              # SQLite 数据库
└── libsimple.dylib     # simple tokenizer 扩展
```

配置通过环境变量管理，写入 `~/.config/fish/conf.d/pkb.fish`：

```fish
set -x PKB_DIR ~/.config/project-kb
set -x PKB_DB_PATH $PKB_DIR/pkb.db
set -x PKB_SIMPLE_EXT $PKB_DIR/libsimple  # 不带扩展名，Python 自动补 .dylib
```

**libsimple 安装**（一次性）：

```bash
# 从 GitHub Releases 下载 macOS arm64 预编译版本
# https://github.com/wangfenjin/simple/releases（当前最新 v0.7.1）
mkdir -p ~/.config/project-kb
cp libsimple.dylib ~/.config/project-kb/libsimple.dylib
```

**DB 初始化**（首次运行自动执行）：

```bash
pkb init   # 创建 ~/.config/project-kb/，建表，加载 simple 扩展验证
```

## CLI 接口

### 项目管理

```bash
pkb project list [--status active]                                             # 列出项目
pkb project add --name "xxx" --desc "..." [--repo "url"] [--path "/本地/路径"]  # 新建项目
pkb project show <id|name>                                                     # 项目详情（含任务统计）
pkb project update <id|name> [--status paused] [--desc "..."] [--repo "..."] [--path "..."]  # 更新字段
pkb project delete <id|name>                                                   # 删除（级联删除 tasks/notes）
```

### 任务管理

```bash
pkb task list --project <id|name> [--status todo] [--priority P1]  # 任务列表
pkb task add --project <id|name> --title "..." [--priority P1] [--desc "..."]  # 新建任务
pkb task show <id>                                                  # 任务详情
pkb task update <id> [--status done] [--priority P0] [--title "..."]  # 更新
pkb task done <id>                                                  # 快捷：标记完成
pkb task delete <id>                                                # 删除
```

### 备忘录

```bash
pkb note add "内容" [--project <id|name>] [--tags "决策,会议"]  # 添加备忘（project 可选）
pkb note list [--project <id|name>] [--limit 10]                 # 列出备忘
pkb note show <id>                                               # 查看详情
pkb note delete <id>                                             # 删除
```

### 搜索

```bash
pkb search "关键词"                        # 全局搜索（中文 + 拼音）
pkb search "xm"                            # 拼音搜索，匹配"项目"等
pkb search "关键词" --project <id|name>    # 限定项目
pkb search "关键词" --type task            # 限定类型 (task / note)
```

**搜索返回格式**：

不返回 relevance 分数（FTS5 的 rank 是负数，暴露出去会让 agent 困惑）。
结果按相关性排序，`results[0]` 最相关，顺序本身即暗示相关性。

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
      "tags": "决策",
      "created_at": "2026-04-21"
    },
    {
      "type": "task",
      "id": "task_yyy",
      "project": "hermes-workspace",
      "title": "...",
      "status": "in_progress",
      "priority": "P1",
      "created_at": "2026-04-20"
    }
  ],
  "count": 2
}
```

### 初始化与工具命令

```bash
pkb init          # 创建 ~/.config/project-kb/，初始化 DB，加载 simple 扩展并验证
pkb status        # 显示 DB 路径、扩展状态、各表记录数
```

### Agent 接口（JSON 输出）

所有命令支持 `--json` 输出：

```bash
pkb search "ntfy" --json
pkb project list --json
pkb task list --project hermes-workspace --json
pkb project show nous-portal-kit --json
```

## 参考 session_search 的设计模式

| session_search                       | pkb 对应                                            |
| ------------------------------------ | --------------------------------------------------- |
| SQLite + FTS5                        | SQLite + FTS5（projects_fts, notes_fts, tasks_fts） |
| external content + trigger 自动同步  | 同上，trigger 保证 FTS 与主表一致                   |
| unicode61 tokenizer                  | simple tokenizer（中文 + 拼音）                     |
| 无 query → 返回最近 session          | 无 search term → 返回最近记录                       |
| 有 query → FTS5 + LLM 总结           | 有 search term → FTS5 返回结构化结果                |
| 不返回 relevance 分数，靠排序暗示    | 同上，不暴露 FTS5 rank 负数值                       |
| \_truncate_around_matches 截取上下文 | 返回完整内容（数据量小，不需要截取）                |
| \_resolve_to_parent 去重             | 按 project 聚合                                     |
| 并发控制 (semaphore)                 | 不需要（本地 SQLite，足够快）                       |
| LLM 总结                             | v2 再做（`pkb summarize --project <id>`）           |

## 与 Agent 集成

### 自动触发

```
用户: "nous-portal-kit 进度怎么样了？"
agent: pkb task list --project nous-portal-kit --json
       → 返回任务列表，整理后回复

用户: "上次关于 ntfy 我们讨论了什么？"
agent: pkb search "ntfy" --json
       → 返回相关 notes，整理后回复
```

### 上下文注入

在 system prompt 中注入项目摘要（类似 memory 注入）：

```
## 项目知识库
- nous-portal-kit: OAuth 客户端，进度 60%，当前在做 token 刷新
- mteam-kit: M-Team API 封装，已完成
```

由 `pkb project list --json` 定期生成并写入 agent 配置。

### Bark 推通知

任务状态变更时推送（可选，在 `task done` / `task update --status` 时触发）：

```bash
curl "$BARK_HOST/pkb更新/任务「xxx」已标记完成"
```

## 技术实现

- **Python 3.12+** + **Click**（CLI 框架，多层子命令结构）
- **SQLite** + FTS5 + **simple tokenizer**（中文 + 拼音搜索）
- ID 生成：`secrets.token_urlsafe(8)`，格式 `proj_<id>` / `task_<id>` / `note_<id>`
- **uv** 管理依赖，pyproject.toml
- **pytest** 测试
- **ruff** lint

**为什么不用 nanoid**：Python 生态里 `nanoid` 包维护状态一般，`secrets.token_urlsafe(8)` 零依赖且足够。

## 验收标准

1. `pkb init` 自动创建 `~/.config/project-kb/`，成功加载 `libsimple.dylib`，`pkb status` 显示 DB 路径和扩展状态
2. `pkb project add --name test --desc "测试项目"` 成功创建
3. `pkb task add --project test --title "做点什么" --priority P1` 关联到项目
4. `pkb note add "今天讨论了 ntfy 推送方案" --project test --tags "决策"` 支持
5. `pkb search "ntfy"` 返回上条 note；`pkb search "jt"` 通过拼音匹配到含"决定"的内容
6. `pkb project show test` 显示项目详情 + 任务统计（todo/done 分类计数）
7. 所有命令 `--json` 输出格式正确，agent 可直接 `json.loads()`
8. `pytest` 全部通过
