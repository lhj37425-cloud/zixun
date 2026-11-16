# PROGRESS：现在做到哪了

> 每完成一个能验证的小步骤，就更新这份文件。最上面永远是"下一步"。

## 下一步（下一个 agent 从这里开始）

- **现在**：B-3.2 准备示例数据（见 [BACKLOG.md](BACKLOG.md)）。开始前先问用户，等用户明确说"开始"。
- **相关文档**：`docs/TECH.md` 第 5 节"数据格式"。

## 进行中

目前没有进行中的条目。

## 卡住的地方

目前没有。

还没定、但暂时不影响开发的事：

- 阿里云服务器的地域和学生包到期时间：影响第 7 步怎么部署。
- TRAE 规则文件的格式：在 B-5.6 里用 TRAE 实测。

## 已完成

| 日期 | 做了什么 | 证据 |
|---|---|---|
| 2026-11-13 | 第 1 步：PRD 定稿（v1.0） | `docs/PRD.md` |
| 2026-11-13 | 实测数据源和本机环境 | 结果记在 `docs/TECH.md` 第 2 节和第 6 节 |
| 2026-11-13 | 第 2 步：写好开发文档（用户验收通过） | `README.md`、`AGENTS.md`、`CLAUDE.md`、`.trae/rules/project_rules.md`、`PROGRESS.md`、`BACKLOG.md`、`docs/TECH.md` |
| 2026-11-13 | 初始化本地 git，提交已验收的 PRD 和开发文档 | 提交 `b729de0` |
| 2026-11-16 | B-3.1 建 Python 项目骨架（用户验收通过） | `uv sync` 装好 23 个包；`uv run pytest`：2 passed；`uv run dd --version`：dd 0.1.0；`.env` 被 `.gitignore` 忽略；提交说明"B-3.1 建 Python 项目骨架" |
