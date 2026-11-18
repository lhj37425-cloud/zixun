"""B-5.3：开始拆解 / 继续拆解复制的指令定稿。"""

from daily_dissect.web.content import DISSECT_INSTRUCTION_TEMPLATE, dissect_instruction


def test_instruction_matches_prd_wording():
    url = "https://github.com/作者/项目名"
    assert dissect_instruction(url) == "请按照 prompts/dissect.md 拆解 https://github.com/作者/项目名"
    assert DISSECT_INSTRUCTION_TEMPLATE == "请按照 prompts/dissect.md 拆解 {url}"


def test_instruction_strips_whitespace_around_url():
    assert (
        dissect_instruction("  https://github.com/foo/bar  ")
        == "请按照 prompts/dissect.md 拆解 https://github.com/foo/bar"
    )


def test_start_and_continue_use_the_same_sentence():
    """继续拆解不另写一句；agent 靠文件夹状态判断从哪一步接着做。"""
    url = "https://github.com/example/agent-demo"
    assert dissect_instruction(url) == f"请按照 prompts/dissect.md 拆解 {url}"
