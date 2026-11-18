# 跑起来：google-labs-code/stitch-skills

先说结论：**这个仓库没有「一个 demo 应用」可以跑**。它是技能说明书，真正干活的是 Google 云端的 Stitch。所以我们今天实际跑通的是它能跑的那部分——**安装、发现、校验脚本**（这些都是真跑过的，命令和输出都在下面），而「让 agent 真去生成一个界面」这一环需要你的 Google 账号和 API Key，我没有代你操作，把要做的步骤写清楚了。

## 需要准备什么

| 需要 | 本机情况 | 说明 |
|---|---|---|
| git | 有 | 只用来下载 |
| Node 18+ | v22.22.2 ✅ | 校验脚本、快照脚本要用 |
| npm | 10.9.7 ✅ | 装 `@swc/core` |
| Python 3 | 3.13.14 ✅ | 只有上传脚本用得上 |
| Stitch MCP | ❌ 未配 | 真正生成界面必须这一环，要 Google 账号 + API Key |
| 磁盘 | 已用约 1 MB（不含 node_modules） | 很轻 |
| 显卡 | 不需要 | 全部在云端 |

**关于 Stitch MCP 到底要什么**（这一步我**没有**执行，因为它要动你的 Google 账号和全局配置）：去 `stitch.withgoogle.com/settings` 里的 API keys 点 Create，拿到一串 key；服务地址是 `https://stitch.googleapis.com/mcp`，鉴权放在请求头 `X-Goog-Api-Key` 里。Stitch 本身对 Google 账号免费，有生成次数限制。Claude Code 里一条命令能挂上：

```bash
claude mcp add stitch --transport http https://stitch.googleapis.com/mcp --header "X-Goog-Api-Key: 你的KEY" -s user
```

> 老实交代：官方的 `stitch.withgoogle.com/docs/mcp/setup/` 这次抓取失败（网络），上面这段是综合几篇第三方教程整理的，**未在本机验证**。等你真要挂的时候我陪你走一遍。

## 安装和运行的每一步

所有命令都在 `sandbox/google-labs-code-stitch-skills/` 里执行。

### 1. 下载仓库

```bash
git clone --depth 1 https://github.com/google-labs-code/stitch-skills sandbox/google-labs-code-stitch-skills
```

`--depth 1` 表示只拉最新一次提交，不拉完整历史——我们只是读代码，不需要历史，快很多。

### 2. 先看清里面有什么，再动手

```bash
find . -not -path "./.git/*" -type f | wc -l
```

结果：**88 个文件**。再看目录，只有三样东西：`plugins/`（三个插件）、`.agents/plugins/marketplace.json`（插件市场清单）、`.github/workflows/`（自动检查）。没有 `package.json` 在主目录，没有 `requirements.txt`——**它不是一个要「安装」的程序，是一堆要被「读」的文档**。这点想明白，后面就不会白折腾。

### 3. 数一数到底有几个技能

```bash
npx --yes plugins discover .
```

输出（真跑过）：

```text
◇  Found 3 local plugin(s)
│  stitch-build      5 skills  Code generation and build tools for Google Stitc…
│  stitch-design     6 skills  Design workflows for Google Stitch: convert code…
│  stitch-utilities  5 skills  Design utilities for Google Stitch: generate DES…
```

5 + 6 + 5 = **16 个技能**，和 README 对得上。这一步挺有用：以后你拿到任何一个技能仓库，都可以先 `discover` 一眼，不用一个个翻文件夹。

### 4. 装依赖，跑那个「检查代码合不合格」的脚本

只有 `react-components` 和 `react-native` 这两个技能需要装依赖，其余是纯 Markdown。

```bash
cd plugins/stitch-build/skills/react-components
npm ci
```

`npm ci` 和 `npm install` 的区别：`ci` 严格照 `package-lock.json` 装，不改版本，适合「照抄别人的环境」。结果：**装了 4 个包，19 秒**（主要是 `@swc/core`）。

然后拿它自带的「标准答案」试一下校验器：

```bash
node scripts/validate.js examples/gold-standard-card.tsx
```

### 5. 故意写坏一个，看它拦不拦

这是今天最值钱的一步——**验证「检查」本身有没有用**。我写了个小脚本，从标准示例里删掉 `Props` 接口、再往 `className` 里塞一个 `text-[#1A73E8]`，然后跑同一个校验器：

```bash
node scripts/validate.js .broken-demo.tsx
```

（临时文件跑完已删除。）

### 6. 试另外两个脚本（不需要 Stitch 账号就能试的部分）

```bash
# HTML 快照脚本：读一个正在跑的网页，把它存成单文件 HTML
npx --yes tsx plugins/stitch-design/skills/extract-static-html/scripts/snapshot.ts --help

# 上传脚本：把本地文件推到 Stitch 项目里
python plugins/stitch-design/skills/upload-to-stitch/scripts/upload_to_stitch.py --help

# 下载脚本：从 Stitch 给的临时链接把 HTML/截图 curl 下来
bash plugins/stitch-build/skills/react-components/scripts/fetch-stitch.sh
```

### 7. 试着「装进 agent」（结论：换个方式装）

```bash
npx --yes plugins add ../google-labs-code-stitch-skills --target claude-code --scope project -y
```

失败，原因见下一节。

## 遇到的问题和解决办法

**问题 1：`--scope project` 装不进去。**

```text
■  Could not complete the command.
│  Scope "project" is not supported for Claude Code with this source.
```

这个 CLI 目前只允许 `vercel/vercel-plugin` 用 project/local 范围，别的仓库只能装到用户级（会写进 `C:\Users\1\.claude`，对你所有项目生效）。

**我没有替你执行用户级安装**——那会改你的全局 Claude 配置。两个选择，你挑一个我就做：
- 用户级装（`-s user`，去掉 `--scope project`）：一次装好，所有项目都能用。
- 只给某个项目用：手动把需要的技能文件夹拷进那个项目的 `.claude/skills/`。

我先把第二条在 `sandbox/stitch-install-test/` 里演示了一遍：

```bash
mkdir -p .claude/skills
cp -R ../google-labs-code-stitch-skills/plugins/stitch-build/skills/react-components .claude/skills/
```

成了。**但有个坑**：`cp -R` 把 `node_modules` 一起搬过去了（几百 MB 的垃圾被复制进你的项目）。拷之前先删掉，或者只拷 `SKILL.md`、`scripts/`、`resources/`、`examples/`、`package.json`。

**问题 2：HTML 快照脚本跑不起来。**

```text
Error: Cannot find module 'puppeteer'
```

因为 `extract-static-html` 这个技能**没有带 `package.json`**，`puppeteer`（一个能开无头浏览器截图的库）得你自己装，还得额外下载一个 Chromium（约 150–300 MB）。我没继续装——今天的目标是看懂结构，不是装浏览器。要用的时候：

```bash
npm i puppeteer && npx puppeteer browsers install chrome
```

**问题 3：`fetch-stitch.sh` 不带参数直接跑会退 1。**

这是设计如此，它是用法提示：

```text
Usage: scripts/fetch-stitch.sh <url> <output_path>
```

真正的下载我**没有执行**：Stitch 给的下载链接是临时的，几分钟到几小时就过期，没有真实项目拿不到有效链接。

**问题 4：`upload_to_stitch.py` 必须带 API Key。**

`--help` 里能看出它的三个必填参数：`--project-id`、`--file-path`、`--api-key`。没有 key 就没跑。这个脚本的注释写得很实在，值得单独说：

> 模型没法直接用 MCP 工具上传文件，因为工具参数是模型「输出」的一部分。模型输出上限约 16K token，而一个 53KB 的 PNG 转成 base64 有 7 万多字符，会被截断，发出去就是坏数据。

所以它绕开模型，自己在进程里读文件、编码、直接用 HTTP 发出去。**这就是「哪些活不该交给模型干」的活教材**——凡是「把大块字节搬过去」的事，都该写成脚本，让 agent 只负责调用。

## 跑起来之后看到了什么

**校验器对「标准答案」放行**（真输出）：

```text
🔍 Scanning AST...
--- Validation for: gold-standard-card.tsx ---
✅ Props declaration found.
✅ No hardcoded hex values found.

✨ COMPONENT VALID.
```

退出码 0。

**校验器对写坏的版本拦下**（真输出）：

```text
🔍 Scanning AST...
--- Validation for: .broken-demo.tsx ---
❌ MISSING: Props interface (must end in 'Props').
❌ STYLE: Found 1 hardcoded hex codes.
   - text-[#1A73E8] flex items-center justify-between gap-4 rounded-lg ...
🚫 VALIDATION FAILED.
```

退出码 1。**注意它是先 AST 扫描、再报错**：`🔍 Scanning AST...` 这行说明它是把 TSX 解析成语法树后判断结构，而不是文字搜索。所以就算某个文件的注释里写着 `interface FooProps`，也不会被骗过。

**插件发现**：3 个插件、16 个技能，一目了然（输出见上）。

**手动装进项目**：`.claude/skills/react-components/` 下的 `SKILL.md`、`scripts/`、`resources/`、`examples/` 结构完整——这就是 agent 启动时会扫的路径。

**没跑到的部分**（如实标注）：
- 真的让 Stitch 生成一张界面 —— 未执行（缺 API Key）
- 真的下载 Stitch 的 HTML/截图 —— 未执行（缺有效的临时链接）
- 真的把设计转成 React 组件并跑起来 —— 未执行（依赖上一条）
- 真的在 Claude Code 里看到技能被自动加载 —— 未执行（改了全局配置要先问你）

想补哪一段，跟我说一句就行。最低成本的下一步是：**你去 Stitch 网页里手动生成一张界面、拿到 API Key**，这样后面的环节就全通了。
