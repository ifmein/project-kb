# pkb — Project Knowledge Base

CLI 工具，SQLite + FTS5 存储，作为 agent 的项目知识库后端。
支持中文分词和拼音搜索（libsimple tokenizer），所有命令均可 `--json` 输出，方便 agent 直接调用。

## 快速上手

```bash
# 克隆并安装
git clone <repo>
cd project-kb
uv sync

# 初始化（创建 ~/.config/project-kb/，复制 libsimple.dylib，建表）
uv run pkb init

# 按提示将环境变量写入 fish config，然后重新加载
```

`pkb init` 会打印如下片段，加到 `~/.config/fish/conf.d/pkb.fish`：

```fish
set -x PKB_DIR ~/.config/project-kb
set -x PKB_DB_PATH $PKB_DIR/pkb.db
set -x PKB_SIMPLE_EXT $PKB_DIR/libsimple  # 不带扩展名
```

## 命令参考

### 项目

```bash
pkb project list [--status active]
pkb project add --name "xxx" --desc "..."
pkb project show <id|name>
pkb project update <id|name> [--status paused] [--desc "..."] [--repo "..."] [--stack "..."]
pkb project delete <id|name> [--yes]
```

### 任务

```bash
pkb task list --project <id|name> [--status todo] [--priority P1]
pkb task add --project <id|name> --title "..." [--priority P1] [--desc "..."]
pkb task show <id>
pkb task update <id> [--status in_progress] [--priority P0] [--title "..."] [--desc "..."]
pkb task done <id>          # 快捷：标记完成
pkb task delete <id>
```

### 备忘录

```bash
pkb note add "内容" [--project <id|name>] [--tags "决策,会议"]
pkb note list [--project <id|name>] [--limit 20]
pkb note show <id>
pkb note delete <id>
```

### 搜索

```bash
pkb search "ntfy"                         # 全文搜索，中文 + 拼音
pkb search "jue ce"                       # 拼音搜索，匹配"决策"
pkb search "ntfy" --project <id|name>     # 限定项目
pkb search "ntfy" --type note             # 限定类型 (task / note)
pkb search "ntfy" --json                  # JSON 输出
```

搜索结果格式（`--json`）：

```json
{
  "success": true,
  "query": "ntfy",
  "results": [
    { "type": "note", "id": "note_xxx", "project": "my-proj", "content": "...", "tags": "决策", "created_at": "2026-04-23" },
    { "type": "task", "id": "task_yyy", "project": "my-proj", "title": "...", "status": "todo", "priority": "P1", "created_at": "2026-04-23" }
  ],
  "count": 2
}
```

### 工具命令

```bash
pkb init      # 初始化配置目录 + DB
pkb status    # 显示 DB 路径、扩展加载状态、各表记录数
```

## 环境变量

| 变量             | 默认值                        | 说明                                                         |
| ---------------- | ----------------------------- | ------------------------------------------------------------ |
| `PKB_DB_PATH`    | `~/.config/project-kb/pkb.db` | 数据库路径                                                   |
| `PKB_SIMPLE_EXT` | _(未设置)_                    | libsimple 路径，不带 `.dylib` 后缀；未设置时降级为 unicode61 |

## 项目结构

```
pkb/
├── cli.py              # 根 Click group，注册所有子命令
├── db.py               # SQLite 连接、DDL、FTS5 虚拟表、triggers
├── models.py           # make_id(), now(), fmt_ts()
├── options.py          # json_option 装饰器 + get_json_flag()
├── output.py           # Rich 表格/面板输出 + JSON helpers
└── commands/
    ├── init_cmd.py     # pkb init / pkb status
    ├── project.py      # pkb project *
    ├── task.py         # pkb task *
    ├── note.py         # pkb note *
    └── search.py       # pkb search
reference/
└── libsimple-osx-arm64/
    └── libsimple.dylib # simple tokenizer 预编译版（macOS arm64）
tests/
    conftest.py         # fixtures: db_path, runner, project_name
    test_project.py
    test_task.py
    test_note.py
    test_search.py      # 含 pinyin test（需 PKB_SIMPLE_EXT）
```

## 开发

```bash
uv run pytest -v          # 运行测试（需设置 PKB_SIMPLE_EXT 才会跑 pinyin 测试）
uv run ruff check pkb/    # lint
uv run ruff format pkb/   # format
```

## 数据模型

- **projects**: `id(proj_*)`, `name(unique)`, `description`, `status(active/paused/completed/archived)`, `repo_url`, `tech_stack`, `created_at`, `updated_at`
- **tasks**: `id(task_*)`, `project_id(FK)`, `title`, `description`, `status(todo/in_progress/done/cancelled)`, `priority(P0-P3)`, `assignee`, `due_date`, `created_at`, `updated_at`
- **notes**: `id(note_*)`, `project_id(FK,nullable)`, `content`, `tags`, `created_at`
- **notes_fts / tasks_fts**: FTS5 external content 虚拟表，3 triggers 自动同步

## v2 计划

- `pkb summarize --project <id>` — LLM 总结项目状态
- `task done` / `task update --status` 时触发 Bark 推送通知
