# 今日一拆 · 技术方案（TECH）

> 更新：2026-11-16 · 对应 PRD v1.2
>
> 这份文件回答：用什么技术、项目结构是怎样的、数据长什么样、怎么运行。技术方案或环境有变化时更新它，并在第 10 节的决策记录里写明原因。

## 1. 技术选择

| 用途 | 选择 | 说明 |
|---|---|---|
| 编程语言 | Python 3.14 | 本机已安装 3.14.7 |
| 依赖管理 | uv | 本机已安装 0.11.33。用 `uv sync` 安装依赖，用 `uv run` 运行命令 |
| 测试 | pytest | |
| 抓网页和 RSS | httpx、feedparser、beautifulsoup4 | httpx 发请求，feedparser 解析 RSS，beautifulsoup4 解析 Trending 页面 |
| 生成网页 | 自己写的小生成器：Jinja2 模板 + markdown-it-py | 把 `content/` 里的 JSON 和 Markdown 生成静态网页 |
| 流程图 | Mermaid 12.3.0（MIT 许可） | 用单文件版 `mermaid.min.js`（约 5.4MB），放在项目里，不从国外网站加载 |
| 大模型 | DeepSeek API | 走 OpenAI 兼容接口，直接用 httpx 调用 |
| 读取密钥 | python-dotenv | 从 `.env` 读取 API Key |
| 看网页 | 浏览器直接打开 `site/index.html` | 网页是生成好的静态文件，不用开服务；`uv run dd open` 会先生成再打开 |
| 定时运行 | Windows 任务计划程序 | 系统自带，支持"错过计划时间后尽快运行" |

## 2. 运行环境（2026-11-13 实测）

- 系统：Windows 11
- 已安装：Python 3.14.7、uv 0.11.33、Git 2.55.0、Node.js 24.21.0（本项目暂时不用 Node）
- 项目位置：`D:\GitHub 项目\daily-dissect`
- 网络：GitHub 网站在用户的网络下打开偏慢，但用程序抓取 Trending 页面约 3 秒就能完成
- 依赖：B-3.1 实际装上的版本都记在 `uv.lock` 里，比如 httpx 0.28.1、feedparser 6.0.14、beautifulsoup4 4.15.0、jinja2 3.1.6、markdown-it-py 4.3.0、python-dotenv 1.2.4、pytest 9.2.0

## 3. 整体架构

整个系统 = 一个每日工作流 + 一个静态网页 + 现成的 agent，三者通过同一个项目文件夹连接。

每天的流程：

1. 9:00，任务计划程序启动每日工作流。
2. 项目线和资讯线同时运行，各自产出结果。
3. 两条线的结果合并，写入 `content/daily/日期.json`。
4. 生成器根据 `content/` 生成网页，放到 `site/`。
5. 用户在电脑浏览器里打开今日页（双击 `site/index.html` 或点收藏），点"开始拆解"，把指令粘贴给 Claude Code 或 TRAE。
6. agent 按 `prompts/dissect.md` 拆解，结果写进 `content/projects/`。
7. 重新生成网页，拆解页显示最新进度。

### 3.1 项目线：今天拆哪个

1. 抓取 GitHub Trending（每天）。
2. 检查 HelloGitHub 有没有出新一期；出了就把新一期的项目放进项目池。
3. 把今天 Trending 上的项目也放进项目池。超过 30 天没再出现的候选移出项目池（HelloGitHub 当前这一期的项目除外）。
4. 排除以前当过主推的项目，以及已经开始拆的项目（`content/projects/` 里有它的文件夹）。
5. **DeepSeek 第 1 次调用**：给所有候选打分，只输出分数（和 AI、agent 的相关度，零基础好不好上手）。
6. 取总分前 3：第 1 名是主推，第 2、3 名是备选。

### 3.2 资讯线：今天该知道什么

1. 按 `config/sources.toml` 逐个抓取 RSS，每个源最多等 20 秒，失败就跳过并记下原因。
2. 只保留最近 24 小时发布的内容；链接完全相同的只留一条。
3. **DeepSeek 第 2 次调用**：把说同一件事的几条合并成一组，每组打分并分进 4 个栏目，只输出编号、栏目和分数。
4. 取前 5 条，同一个栏目最多 2 条。

### 3.3 写说明

**DeepSeek 第 3 次调用**：只给入选的 3 个项目和最多 5 条资讯写说明（一句话介绍、能解决谁的什么问题、对你的价值等）。先粗筛、再只给入选的写说明，这样每天固定调用 3 次，token 用量可以预期。

### 3.4 两条线互不影响

两条线同时运行。一条线出错，只把这条线的状态记成"失败"并写下原因，另一条照常完成。

### 3.5 没有 DeepSeek 时的兜底

没配置 API Key 或者调用失败时，用关键词规则打分（名字和简介里出现 agent、LLM、模型、智能体等词就加分），说明字段留空，网页上标"未生成解读"。整个流程照样能跑完。

### 3.6 网页

- 生成器读取 `content/` 里的文件，套用模板，生成 4 个页面到 `site/`。
- Markdown 里的 ` ```mermaid ` 代码块转成 `<pre class="mermaid">`，由本地的 `mermaid.min.js` 画成图。
- 只有拆解详情页加载 Mermaid，今日页不加载，保证今日页打开快。
- 打开方式：浏览器直接打开 `site/` 里的网页文件（地址以 `file://` 开头），不开服务。所有链接都用相对路径。所以页面里不能用只有开着服务才能工作的写法，比如用脚本去读取 JSON 文件（fetch），或者 ES module 版的 Mermaid；这也是选单文件版 `mermaid.min.js` 的原因。
- 复制按钮：先用浏览器的剪贴板接口（直接打开文件时能用，B-3.5 用 Edge 实测过）；用不了时换成兼容写法（临时文本框 + 复制命令），以后手机通过局域网 http 打开时会走这条路；两种都失败时弹出要复制的内容，让用户手动复制。

**设计规范**（2026-11-16 用 UI/UX Pro Max 审过今日页之后定下，4 个页面和以后的生成器都照这个来）：

- 风格：极简瑞士风。干净、留白、对比清楚，靠字号和排版分层次，不靠装饰。
- 颜色、字号、间距、圆角都用 `src/daily_dissect/web/static/style.css` 顶部的变量，组件里不直接写颜色；亮色和暗色两套变量一起改。
- 文字和背景的对比度至少 4.5:1，亮色、暗色都要算过。
- 手机（768 像素以下）：内容排成一列，按钮和导航至少 44 像素高，不能出现横向滚动。第一版只在电脑上看，但页面先按这个排好，以后升级到手机不用重做。
- 键盘：焦点框要看得见；页面最前面有"跳到正文"链接。
- 图标：用 Feather 线条图标，直接写在页面里，不用 emoji，也不从网上加载。
- 字体：只用系统字体（苹方、微软雅黑等），不加载网络字体。
- 动效：只用在悬停和按下的反馈上（150 毫秒）；系统开了"减少动画"就全部关掉。
- 读屏软件：装饰性图标对它隐藏；拆解进度要写明"已完成"或"未完成"；复制的结果会念出来。

**原型里定下的做法**（B-3.4 写生成器时照着做）：

- 每个页面开头的图标定义完全一样，生成器把它做成一个公共片段。
- 今日页的大标题是"今日一拆 + 日期"；其他页面的大标题是页面名，顶部的"今日一拆"只是普通链接。
- 某一天的页面和今日页用同一个模板：标题换成日期，加上面包屑"往期 / 日期"，主推的标签写"当天主推"。
- 没用上 DeepSeek 时：项目显示原始的英文简介，区块开头放一个提示框说明原因；某条线失败时，在那个区块放红色提示框，写明原因和怎么补救。
- 拆解文件里的一级标题（比如"# 一页纸：……"）不显示，页面自己有标题；Markdown 里的引用、标题、列表按 `.prose` 的样式显示。
- 流程图脚本（`diagrams.js` 和 `mermaid.min.js`）只在拆解详情页加载；亮色、暗色切换时会自动用对应的主题重画。
- 拆解详情页：没拆完时，在四步进度下面放"继续拆解"按钮，复制的指令和"开始拆解"一样；四步都完成后不显示。这一页也要加载 `app.js` 和读屏提示区。
- 网站根目录要放 `favicon.ico`：就算页面声明了 SVG 图标，浏览器还是会来要它，没有就会报 404。

### 3.7 agent 连接

- **规则**：`AGENTS.md` 写开发规则；`CLAUDE.md` 用一行 `@AGENTS.md` 引用它；TRAE 的 `.trae/rules/project_rules.md` 用一句话指向它（格式在 B-5.6 用 TRAE 实测）。
- **拆解说明**：`prompts/dissect.md`，在 B-5.1 写。
- **复制的指令**："请按照 prompts/dissect.md 拆解 https://github.com/作者/项目名"。
- **agent 拆解时要做的事**（详细写在 `prompts/dissect.md`）：用 `uv run dd new-project <仓库>` 建项目文件夹；把对方的项目下载到 `sandbox/`；按四步写文件；新概念写进术语表；最后运行 `uv run dd build` 重新生成网页。命令名是计划，开发时以实际为准。

## 4. 项目结构

### 4.1 开发文档（已建）

```
daily-dissect/
├─ README.md                     # 给人看的说明
├─ AGENTS.md                     # agent 的开发规则
├─ CLAUDE.md                     # 一行：@AGENTS.md
├─ .trae/rules/project_rules.md  # 一句话：去读 AGENTS.md
├─ PROGRESS.md                   # 做到哪、证据、卡在哪、下一步
├─ BACKLOG.md                    # 待办和优先级
└─ docs/
   ├─ PRD.md                     # 产品需求（已定稿）
   └─ TECH.md                    # 本文件
```

### 4.2 项目架构（设计图，开发到哪一步再建哪部分）

```
daily-dissect/
├─ pyproject.toml          # Python 项目配置和依赖（B-3.1，已建）
├─ uv.lock                 # uv 记下的确切依赖版本，要提交（B-3.1，已建）
├─ .python-version         # 指定用 Python 3.14（B-3.1，已建）
├─ .env.example            # 只写变量名（B-3.1，已建）
├─ .gitignore              # 不提交 .env、.venv/、site/、sandbox/、logs/（B-3.1，已建）
├─ .gitattributes          # 换行符规则：普通文件用 LF，.bat 用 CRLF（B-3.1，已建）
├─ .venv/                  # uv 建的 Python 环境，不提交
├─ src/daily_dissect/
│  ├─ __init__.py          # 版本号（B-3.1，已建）
│  ├─ paths.py             # 项目里各个文件夹的位置（B-3.4，已建）
│  ├─ cli.py               # 命令入口：dd build、dd open、dd radar 已能用；new-project 后面再加
│  ├─ sources.py           # 读取 config/sources.toml（B-4.1，已建）
│  ├─ projects/            # 项目线：解析 Trending/HelloGitHub、项目池（B-4.2，已建；打分挑选在后面）
│  │  ├─ trending.py       # 解析 Trending HTML
│  │  ├─ hellogithub.py    # 解析 RSS 期号和某一期 Markdown
│  │  ├─ pool.py           # data/pool.json 读写、去重、30 天过期
│  │  ├─ sync.py           # 把解析结果写进项目池
│  │  └─ fetch.py          # 真正发请求抓网页（radar 时用）
│  ├─ news/                # 资讯线：RSS 抓取、24 小时过滤、去重（B-4.3，已建；合并分栏在后面）
│  │  ├─ parse.py          # 解析 RSS/Atom，过滤与去重
│  │  ├─ fetch.py          # 单个源抓取（超时 20 秒）
│  │  └─ collect.py        # 汇总全部源，记录失败原因
│  ├─ prompts.py           # 读取 prompts/ 说明文件（B-4.4，已建）
│  ├─ llm/                 # 调用 DeepSeek，以及关键词兜底（B-4.5，已建）
│  │  ├─ client.py         # DeepSeek 客户端 + 测试用假模型
│  │  ├─ fallback.py       # 关键词打分；说明字段留空
│  │  └─ pipeline.py       # 每天固定 3 次调用的编排
│  ├─ radar/               # 每日工作流：挑选并写入今日数据（B-4.6，已建）
│  │  ├─ select.py         # 排除已主推/已拆解；挑前 3 项目、最多 5 条资讯
│  │  ├─ build.py          # 拼今日 JSON
│  │  └─ run.py            # 抓取 + 挑选 + 写盘（dd radar）
│  └─ web/                 # 网页生成器（B-3.4，已建）
│     ├─ content.py        # 读取 content/，整理成页面要用的样子
│     ├─ markdown.py       # 把拆解文件的 Markdown 转成网页内容
│     ├─ build.py          # 生成全部页面到 site/
│     ├─ templates/        # 页面模板：base、_macros、_icons、day、history、projects、project、glossary
│     └─ static/           # 样式、脚本、图标、vendor/mermaid.min.js（从原型复制过来）
├─ tests/                  # 自动化测试
│  └─ fixtures/
│     ├─ content/          # 网页生成器用的固定示例数据
│     ├─ projects/         # Trending / HelloGitHub 样例页面（B-4.2）
│     └─ news/             # RSS/Atom 样例（B-4.3）
├─ config/sources.toml     # 信源清单（B-4.1，已建）
├─ prompts/
│  ├─ profile.md           # 你的画像：水平、目标（给模型看）（B-4.4，已建）
│  ├─ score-projects.md    # 项目线打分标准（B-4.4，已建）
│  ├─ score-news.md        # 资讯线打分和分栏标准（B-4.4，已建）
│  ├─ write.md             # 给入选项目/资讯写说明（B-4.5，已建）
│  └─ dissect.md           # 拆解四步法（B-5.1）
├─ content/
│  ├─ daily/               # 每天一份今日数据（B-3.2，已放示例）
│  ├─ projects/            # 每个拆解项目一个文件夹（B-3.2，已放示例）
│  └─ glossary.md          # 术语表（B-3.2，已建）
├─ data/pool.json          # 项目池（B-4.2）
├─ scripts/update.bat      # 双击手动更新（B-6.1）
├─ （prototype/ 已删除）     # 手写的页面原型（B-3.3），B-3.4 验收后删掉了；要看可以找 git 提交 e92b35f
├─ site/                   # dd build 生成的网页，不提交；里面的 .dd-site 是生成器的标记
├─ sandbox/                # 拆解时下载的别人的项目，不提交
└─ logs/                   # 运行记录，不提交
```

文件名一律用英文，避免不同工具处理中文文件名时出问题；文件里的内容用中文。

## 5. 数据格式

### 5.1 今日数据：`content/daily/YYYY-MM-DD.json`

日期按北京时间。下面是一份示例：

```json
{
  "date": "2026-11-14",
  "generated_at": "2026-11-14T09:00:42+08:00",
  "llm": { "used": true, "model": "deepseek-chat", "calls": 3 },
  "projects": {
    "status": "ok",
    "error": null,
    "pick": {
      "repo": "example/agent-demo",
      "url": "https://github.com/example/agent-demo",
      "slug": "example-agent-demo",
      "source": "GitHub Trending",
      "description": "原始英文简介",
      "language": "Python",
      "stars": 1817,
      "stars_today": 120,
      "score": 8.6,
      "one_liner": "一句话介绍",
      "solves": "能解决谁的什么问题",
      "for_you": "对你有什么价值",
      "why_dissect": "为什么拆它"
    },
    "alternates": []
  },
  "news": {
    "status": "ok",
    "error": null,
    "items": [
      {
        "title": "原标题",
        "url": "https://example.com/post",
        "source": "量子位",
        "published": "2026-11-14T07:30:00+08:00",
        "category": "新能力",
        "score": 8.1,
        "what": "发生了什么",
        "solves": "能解决谁的什么问题",
        "for_you": "对你意味着什么"
      }
    ]
  }
}
```

- `status`：`ok` 或 `failed`。失败时 `error` 写原因，网页据此显示"项目线今天没抓到"或"资讯线今天没抓到"；同时 `projects` 的 `pick` 为 `null`、`alternates` 为空列表，`news` 的 `items` 为空列表。
- `alternates`：最多 2 个，字段和 `pick` 一样，只是没有 `why_dissect`。
- `category`：只能是 `新能力`、`新工具`、`新产品`、`落地案例` 之一。
- 没用上 DeepSeek 时，`llm.used` 为 `false`，说明字段为空字符串，网页显示"未生成解读"。
- `sample`：可选。示例数据写 `true`，网页上会提示"这是示例数据"；真实数据不写这个字段。

### 5.2 项目池：`data/pool.json`

```json
{
  "updated_at": "2026-11-14T09:00:30+08:00",
  "hellogithub_volume": 127,
  "candidates": {
    "example/agent-demo": {
      "repo": "example/agent-demo",
      "url": "https://github.com/example/agent-demo",
      "description": "简介",
      "language": "Python",
      "source": "HelloGitHub 第 127 期 · 人工智能",
      "first_seen": "2026-11-14",
      "last_seen": "2026-11-14"
    }
  },
  "picked": [
    { "date": "2026-11-14", "repo": "example/agent-demo" }
  ]
}
```

- `candidates` 的键是小写的"作者/项目名"，用来去重；`repo` 保留原来的大小写。
- `hellogithub_volume`：已经放进项目池的最新一期，用来判断有没有出新一期。
- `picked`：每天的主推记录。当过主推的不再推荐；备选不记在这里，以后还能再出现。

### 5.3 拆解项目：`content/projects/<slug>/`

- `slug`：仓库名转成小写，"/" 换成 "-"。例如 `LearnPrompt/ai-news-radar` 变成 `learnprompt-ai-news-radar`。
- 文件夹里的文件：

| 文件 | 内容 |
|---|---|
| `meta.json` | `{"repo": "作者/项目名", "url": "...", "started": "YYYY-MM-DD"}`；示例项目再加 `"sample": true` |
| `01-overview.md` | 第 1 步：一页纸 |
| `02-flows.md` | 第 2 步：两张流程图，用 ` ```mermaid ` 代码块 |
| `03-run.md` | 第 3 步：跑起来的过程和每条命令的解释 |
| `04-qa.md` | 第 4 步：追问的问答记录 |

- **怎么判断一步完成了**：文件存在，并且里面没有 `<!-- 待完成 -->` 这个标记。新建项目时，四个文件都带着这个标记。
- 只要这个文件夹存在，就算"已经开始拆"，项目线不会再推荐它。

### 5.4 术语表：`content/glossary.md`

每个术语一个二级标题，下面用一两句话解释，再写一行它第一次出现在哪里：

```markdown
## 工作流
步骤事先写死、每次按同样顺序执行的流程，AI 只在其中某几步干活。
- 第一次出现：今日一拆的设计讨论（2026-11-13）
```

### 5.5 信源清单：`config/sources.toml`

完整清单在仓库里的 `config/sources.toml`（B-4.1）。`projects.*` 是项目线，`[[news]]` 是资讯线。增删或开关某个源，只改这个文件。程序用 `daily_dissect.sources.load_sources` 读取。

```toml
[projects.github_trending]
name = "GitHub Trending"
enabled = true
url = "https://github.com/trending?since=daily"

[projects.hellogithub]
name = "HelloGitHub"
enabled = true
rss = "https://hellogithub.com/rss"
issue_url = "https://raw.githubusercontent.com/521xueweihan/HelloGitHub/HEAD/content/HelloGitHub{volume}.md"
skip_sections = ["开源书籍"]

[[news]]
name = "量子位"
url = "https://www.qbitai.com/feed"
enabled = true

# 其余 10 个资讯源同样格式，地址见第 6 节
```

## 6. 外部接口（2026-11-13 实测）

| 接口 | 地址 | 格式和解析方式 | 实测结果 |
|---|---|---|---|
| GitHub Trending | `https://github.com/trending?since=daily` | HTML。每个项目是一个 `article.Box-row`：仓库名在 `h2 a[href]`，简介在 `p`，语言在 `[itemprop="programmingLanguage"]`，star 数在 `a[href$="/stargazers"]`，今日新增在 `span.float-sm-right`（"643 stars today"） | 能访问，约 3 秒，当天 13 个项目 |
| HelloGitHub 最新期号 | `https://hellogithub.com/rss` | RSS，条目链接形如 `/periodical/volume/127` | 能访问；最新是第 127 期（2026-10-28），每月 28 号出新一期 |
| HelloGitHub 某一期内容 | `https://raw.githubusercontent.com/521xueweihan/HelloGitHub/HEAD/content/HelloGitHub{期号}.md` | Markdown。"### 分类"下面是"序号、[名称](链接)：描述"；链接里 `target=` 后面才是真正的 GitHub 地址 | 能访问；第 127 期有 42 个项目，分类里有"人工智能"和"Skills" |
| DeepSeek | `https://api.deepseek.com/chat/completions` | OpenAI 兼容；请求头 `Authorization: Bearer <Key>`；用 JSON 输出模式 | 还没测（要用户自己的 API Key） |

资讯源（RSS / Atom），11 个都能访问：

| 名称 | 地址 |
|---|---|
| 量子位 | `https://www.qbitai.com/feed` |
| InfoQ 中文 | `https://www.infoq.cn/feed` |
| OpenAI | `https://openai.com/news/rss.xml` |
| Google AI | `https://blog.google/technology/ai/rss/` |
| Hugging Face | `https://huggingface.co/blog/feed.xml` |
| Simon Willison | `https://simonwillison.net/atom/everything/` |
| Latent Space | `https://www.latent.space/feed` |
| smol.ai AI News | `https://news.smol.ai/rss.xml` |
| Hacker News（100 分以上） | `https://hnrss.org/frontpage?points=100` |
| GitHub 博客 | `https://github.blog/feed/` |
| 爱范儿 | `https://www.ifanr.com/feed` |

抓不到条目的源：机器之心（`https://www.jiqizhixin.com/rss`）、36 氪（`https://36kr.com/feed`）、LangChain（`https://blog.langchain.com/rss/`）。

注意：OpenAI、Hugging Face、smol.ai 的 RSS 里带着全部历史文章（几百到上千条），必须按发布时间过滤。

## 7. 运行方式（计划，开发时以实际为准）

目前能用的：`uv sync`、`uv run pytest`、`uv run dd --version`、`uv run dd build`、`uv run dd open`，以及下表最后一行给 agent 用的检查办法。其余命令在后面的条目里逐个加上。

| 想做什么 | 命令 |
|---|---|
| 安装依赖 | `uv sync` |
| 跑一次每日工作流 | `uv run dd radar` |
| 只跑项目线或资讯线 | `uv run dd radar --only projects`、`uv run dd radar --only news` |
| 生成网页 | `uv run dd build` |
| 生成网页，再用浏览器打开今日页 | `uv run dd open`；平时也可以直接双击 `site/index.html`，或者用浏览器收藏 |
| 为要拆的项目建文件夹 | `uv run dd new-project <仓库地址>` |
| 跑测试 | `uv run pytest` |
| agent 在自己的浏览器面板里检查页面（有的面板打不开本地文件；用户平时用不到） | `python -m http.server 8766 --bind 127.0.0.1 --directory site`，然后打开 `http://localhost:8766`；只对本机开放，不会弹防火墙提示 |

## 8. 环境变量（`.env`）

| 变量 | 必填 | 说明 |
|---|---|---|
| `DEEPSEEK_API_KEY` | 否 | 不填就用关键词兜底 |
| `DEEPSEEK_BASE_URL` | 否 | 默认 `https://api.deepseek.com` |
| `DEEPSEEK_MODEL` | 否 | 默认 `deepseek-chat`；DeepSeek 改了模型名就在这里改 |

`.env` 不提交；`.env.example` 只写变量名，不写真实的值。

## 9. 已知风险

| 风险 | 影响 | 应对 |
|---|---|---|
| GitHub 在国内访问不稳定 | 项目线某天可能抓不到 | 两条线互不影响；可以手动只重跑项目线 |
| 海外 RSS 不稳定 | 个别资讯源抓不到 | 单个源失败不影响其他源，失败原因写在页面底部 |
| Trending 页面改版 | 解析不出项目 | `tests/fixtures/` 里存样例页面；改版后测试会失败，按新结构更新解析代码 |
| 项目路径里有中文和空格 | 个别工具可能报路径错误 | 现代工具一般没问题；真遇到了，就把项目移到纯英文路径 |
| DeepSeek 改模型名 | 调用失败 | 模型名放在 `.env` 里，可以直接改；失败时自动走关键词兜底 |
| `mermaid.min.js` 有 5.4MB | 拆解页第一次打开稍慢 | 从本地文件读取，问题不大；今日页不加载它 |
| 9 点电脑没开 | 今日页没更新 | 任务计划设置"错过时间后尽快运行" |
| 以后做手机访问时，在局域网开服务 | Windows 防火墙会弹窗 | 到时候选"允许在专用网络上访问" |

## 10. 技术决策记录

| 日期 | 决定 | 原因 |
|---|---|---|
| 2026-11-13 | 全部用 Python | 只需要学一门语言；Python 是做 AI 和 agent 最常用的语言 |
| 2026-11-13 | 网页用自己写的小生成器 | 今日页的卡片布局能完全按原型做；MkDocs Material 的团队已转去做 Zensical，正处在过渡期；VitePress 需要多学一套 Node 工具 |
| 2026-11-13 | Mermaid 放在本地 | 国内访问国外 CDN 不稳定 |
| 2026-11-13 | 直接用 httpx 调 DeepSeek，不用 OpenAI 的 SDK | 少一个依赖，也能看清楚请求长什么样 |
| 2026-11-13 | 每天调用 DeepSeek 3 次 | 先粗筛打分，再只给入选的写说明，token 用量可以预期 |
| 2026-11-13 | 本地预览用 Python 自带的服务器（2026-11-16 改成直接打开文件，见本表最后一行） | 不用另装软件 |
| 2026-11-13 | 定时用 Windows 任务计划程序 | 系统自带，支持错过时间后补跑 |
| 2026-11-13 | 文件名用英文 | 避免不同工具处理中文文件名时出问题 |
| 2026-11-13 | 你的画像放在 `prompts/profile.md`，不放在 `docs/` | 它是给模型和 agent 看的产品配置，不是开发文档 |
| 2026-11-13 | 用 git 在本地记录版本，不上传 | 用户同意；每一条验收通过后提交一次，出问题能退回，换 agent 也能看到改了什么 |
| 2026-11-13 | 依赖的确切版本记在 `uv.lock` 里并提交 | 换电脑或者换 agent 时，装出来的版本一样 |
| 2026-11-13 | 换行符统一用 LF，`.bat` 保留 CRLF | 以后搬到 Linux 服务器时文件不出问题；`.bat` 在 Windows 上需要 CRLF |
| 2026-11-13 | uv 安装时直接复制文件（`link-mode = "copy"`） | uv 的缓存在 C 盘、项目在 D 盘，跨盘不能用硬链接；这样设置后每次安装不再弹警告 |
| 2026-11-16 | 示例数据加 `sample: true` 标记；某条线失败时 `pick` 为 `null`、列表为空 | 网页能明确提示这是示例，以后清理也好找；失败时的数据长什么样提前定好，网页和工作流按同一个格式来 |
| 2026-11-16 | 用测试检查 `content/` 的格式（`tests/test_content_format.py`） | 网页和工作流都依赖这个格式；格式一旦写错，测试马上就会发现 |
| 2026-11-16 | 先手写页面原型（`prototype/`），用户验收后再写网页生成器 | 用户要求先看样子；这时候改样子成本最低，验收过的原型直接改成模板 |
| 2026-11-16 | 页面按 UI/UX Pro Max 推荐的极简瑞士风优化，规范写在第 3.6 节；没采用它推荐的红色配色、Google 字体和滚动动画 | 用户要求用这个 skill 优化。红色是突发新闻网站的风格，不适合每天安静学习；Google 字体要从国外加载，而且不支持中文；滚动动画对每天阅读没有帮助 |
| 2026-11-16 | 生成器每次先清空 site/，但只清空带 `.dd-site` 标记的文件夹，否则停下来报错 | 防止 `--out` 指错文件夹时误删用户的文件 |
| 2026-11-16 | 生成器的测试用 `tests/fixtures/content/` 里固定的一份示例数据 | 以后 content/ 换成真实数据，测试结果也不会跟着变 |
| 2026-11-16 | "没用上 DeepSeek"的提示写"原始简介"，不写"原始的英文简介"（和原型唯一的文字差别） | HelloGitHub 的项目简介是中文，不能一律说成英文 |
| 2026-11-16 | B-3.4 验收后删除 `prototype/`（用户同意） | 生成器已经能生成一样的页面；原型和 `web/static/` 各留一份样式，以后改样式容易只改一边。原型留在 git 提交 e92b35f 里，随时能找回 |
| 2026-11-16 | 第一版不开本地服务：浏览器直接打开 `site/` 里的网页文件；`dd open` 先生成网页，再交给系统用默认浏览器打开（和双击一样）。原计划的 `dd serve` 不做了 | 用户决定先只在电脑上用（PRD v1.2）。不用一直开着一个服务，开机就能看，也不会弹防火墙提示。B-3.5 用无界面的 Edge 实测：直接打开文件时样式、流程图、亮暗色都正常，剪贴板接口可用 |
