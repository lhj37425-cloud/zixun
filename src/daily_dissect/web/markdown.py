"""把 agent 写的 Markdown 拆解文件转成网页内容。

和普通的 Markdown 转换相比，有三点不同：
1. 文件开头的一级标题（比如"# 一页纸：……"）不显示，页面上每一步自己有标题；
2. 标题整体降一级（## 变成 h3），因为页面上每一步的标题已经是 h2；
3. ```mermaid 代码块变成「查看流程图」按钮，点开全屏舒服看，不在正文里挤着画。
文件里直接写的 HTML 一律当成普通文字显示，不会被执行。
"""

from markdown_it import MarkdownIt
from markupsafe import Markup, escape


def make_markdown() -> MarkdownIt:
    md = MarkdownIt("commonmark", {"html": False}).enable(["table", "strikethrough"])
    default_fence = md.renderer.rules["fence"]

    def render_fence(self, tokens, idx, options, env):
        token = tokens[idx]
        if token.info.strip().lower() == "mermaid":
            code = escape(token.content.rstrip("\n"))
            return (
                '<figure class="diagram-launch">'
                '<button type="button" class="diagram-open" data-diagram-open>'
                "查看流程图"
                "</button>"
                f'<pre class="diagram-source" hidden>{code}</pre>'
                "</figure>\n"
            )
        return default_fence(tokens, idx, options, env)

    def render_table_open(self, tokens, idx, options, env):
        return '<div class="table-scroll"><table>\n'

    def render_table_close(self, tokens, idx, options, env):
        return "</table></div>\n"

    md.add_render_rule("fence", render_fence)
    md.add_render_rule("table_open", render_table_open)
    md.add_render_rule("table_close", render_table_close)
    return md


def render_markdown(md: MarkdownIt, text: str) -> Markup:
    lines = text.lstrip("﻿").splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    if lines and lines[0].startswith("# "):
        lines = lines[1:]

    tokens = md.parse("\n".join(lines))
    for token in tokens:
        if token.type in ("heading_open", "heading_close"):
            level = min(int(token.tag[1]) + 1, 6)
            token.tag = f"h{level}"
    return Markup(md.renderer.render(tokens, md.options, {}))


def has_mermaid(text: str) -> bool:
    return "```mermaid" in text
