# 今日一拆（daily-dissect）

每天上午自动挑出值得拆的 AI 项目和值得知道的 AI 资讯，再带你用四步法，把一个项目从"它解决谁的什么问题"一路拆到"亲手跑起来"。

> **现在的状态**：开发前的准备阶段（开发顺序第 2 步），还不能运行。进度见 [PROGRESS.md](PROGRESS.md)。

## 由哪三部分组成

- **每日工作流**：每天 9 点自动运行，分成项目线和资讯线，结果合到今日页。
- **网页**：唯一的阅读入口，一共 4 页：今日、往期、拆解、术语表。
- **agent**：Claude Code 或 TRAE。按 `prompts/dissect.md` 拆解项目，把结果写回项目文件夹。

## 文档在哪

| 想知道 | 看哪份 |
|---|---|
| 做什么、为什么做、怎么验收 | [docs/PRD.md](docs/PRD.md) |
| 用什么技术、项目结构、数据格式、怎么运行 | [docs/TECH.md](docs/TECH.md) |
| agent 改代码时要遵守什么 | [AGENTS.md](AGENTS.md) |
| 现在做到哪、证据、卡在哪 | [PROGRESS.md](PROGRESS.md) |
| 接下来做什么、优先级 | [BACKLOG.md](BACKLOG.md) |

`CLAUDE.md` 和 `.trae/rules/project_rules.md` 各只有一行，作用是让 Claude Code 和 TRAE 自动去读 `AGENTS.md`。

## 怎么用

具体命令等开发完成后补上。计划中的用法：

- 每天 9 点自动更新，不用管；那时电脑没开，开机后会补跑。
- 想手动更新，双击 `scripts/` 里的更新脚本。
- 在浏览器里打开本地网页；手机连同一个 Wi-Fi 也能看。

## 开发环境

第一次使用，或者依赖有变化时，在项目文件夹里运行一次：

```bash
uv sync
```

跑测试：

```bash
uv run pytest
```

## 换一个 agent 接着做

在 Claude Code 或 TRAE 里打开这个文件夹，说一句：

> 先读 AGENTS.md，再按 PROGRESS.md 里的"下一步"继续。
