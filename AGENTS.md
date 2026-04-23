# AGENTS.md — pkb (Project Knowledge Base)

CLI 工具，SQLite + FTS5 存储，作为 agent 的项目知识库后端。
支持中文分词和拼音搜索（libsimple tokenizer），所有命令均可 `--json` 输出，方便 agent 直接调用。

## 项目定位

`pkb` 是一个 CLI 工具，用 SQLite + FTS5 存储项目、任务、备忘录，支持中文分词和拼音搜索。
主要供 agent 调用（`--json` 输出），也可手动 CLI 使用。仅在本机运行。

## 关键技术决策

| 决策           | 选择                                | 原因                                               |
| -------------- | ----------------------------------- | -------------------------------------------------- |
| 搜索 tokenizer | libsimple（外部 .dylib）            | 支持拼音搜索，trigram 不行                         |
| FTS5 同步方式  | external content + trigger          | 保证一致性，无需手动维护 FTS                       |
| ID 生成        | `secrets.token_urlsafe(8)` + prefix | 零依赖，格式 `proj_*/task_*/note_*`                |
| CLI 框架       | Click >= 8.1                        | 多层子命令，`--json` 装饰器复用                    |
| 包管理         | uv                                  | 所有命令通过 `uv run pkb ...`                      |
| 输出           | Rich（human）/ json.dumps（agent）  | `--json` 在每个叶命令上单独注册（不只在 group 上） |

## 目录结构

```
pkb/
├── cli.py              # 根 group，注册所有子命令
├── db.py               # get_db(), init_db(), load_extension(), _get_tokenizer()
├── models.py           # make_id(prefix), now(), fmt_ts(ts)
├── options.py          # json_option 装饰器, get_json_flag(ctx, local)
├── output.py           # print_*/output_json/error_json 等所有输出函数
└── commands/
    ├── init_cmd.py     # pkb init, pkb status
    ├── project.py      # pkb project list/add/show/update/delete
    ├── task.py         # pkb task list/add/show/update/done/delete
    ├── note.py         # pkb note add/list/show/delete
    └── search.py       # pkb search (FTS5 UNION 查询)
reference/
└── libsimple-osx-arm64/libsimple.dylib   # macOS arm64 预编译版
tests/
    conftest.py         # db_path(tmp), runner, project_name fixtures
    test_project.py     # 9 tests
    test_task.py        # 8 tests
    test_note.py        # 6 tests
    test_search.py      # 8 tests（含 pinyin，需 PKB_SIMPLE_EXT）
```

## 环境变量

| 变量             | 默认值                        | 说明                                                  |
| ---------------- | ----------------------------- | ----------------------------------------------------- |
| `PKB_DB_PATH`    | `~/.config/project-kb/pkb.db` | DB 路径                                               |
| `PKB_SIMPLE_EXT` | _(未设置)_                    | libsimple 路径（不带 `.dylib`）；未设置降级 unicode61 |

`pkb init` 会自动把 `libsimple.dylib` 从 `reference/` 复制到 `~/.config/project-kb/`，并打印 fish 配置片段。

## 运行与测试

```bash
uv run pkb init           # 初始化（首次）
uv run pkb status         # 确认扩展加载状态
uv run pytest -v          # 31 tests（有 PKB_SIMPLE_EXT 时全跑；否则 pinyin 跳过）
uv run ruff check pkb/
```

## 数据库 Schema 要点

- `tasks` / `notes` 有对应的 FTS5 虚拟表（`tasks_fts` / `notes_fts`），各 3 个 trigger 自动同步
- `projects` 同样有 `projects_fts` 虚拟表，搜索时覆盖项目名和描述
- `get_db()` 内部自动调用 `load_extension()`，调用方无需额外操作
- `init_db()` 是幂等的（`CREATE TABLE IF NOT EXISTS`），重复调用安全；内部调用 `_migrate()` 对已有 DB 补列
- FTS5 tokenizer 在 `init_db()` 时固化进 schema，修改 tokenizer 需重建表
- `projects` 字段：`id`, `name`, `description`, `status`, `repo_url`, `local_path`, `tech_stack`, `created_at`, `updated_at`

## `--json` 实现模式

Click group 的 option 必须在子命令名之前传入，因此 `--json` 同时注册在每个叶命令上：

```python
# pkb/options.py
def json_option(f):
    return click.option("--json", "as_json", is_flag=True, default=False)(f)

def get_json_flag(ctx, local_as_json):
    return local_as_json or ctx.obj.get("json", False)
```

用法：在每个命令函数上加 `@json_option`，内部调用 `get_json_flag(ctx, as_json)`。

## 搜索实现

`pkb/commands/search.py` 中 `_search_db()` 对 `notes_fts` 和 `tasks_fts` 分别查询后 UNION，
按 FTS5 rank 升序排列（更负 = 更相关），返回前不暴露 rank 值。

拼音搜索需要空格分隔的全拼，不支持声母缩写：

- ✅ `jue ce`（匹配"决策"）
- ❌ `jc`（libsimple 不支持首字母缩写）

## 已知限制 / v2 TODO

- [ ] `pkb summarize --project <id>` — LLM 总结（需接入 LLM API）
- [ ] `task done` / `task update --status` 触发 Bark 推送（`BARK_HOST` env var）
- [ ] libsimple 仅支持 macOS arm64；Linux/x86 需另行编译或降级 unicode61
- [ ] `note` 无 update 命令（PRD 未要求，如需添加参考 `task update` 实现）

## 常见问题

**`no such tokenizer: simple`**
→ `PKB_SIMPLE_EXT` 未设置。运行 `pkb init`，然后将打印的 fish 配置加入 shell。

**`uv run pkb` 找不到命令**
→ `uv sync` 先安装依赖，或检查 `pyproject.toml` 中 `[tool.hatch.build.targets.wheel] packages = ["pkb"]`。

**FTS5 hyphen 解析错误**（如搜索 `my-term`）
→ FTS5 把 `-` 解析为 NOT 操作符。将连字符替换为空格或去掉：`pkb search "myterm"`。
