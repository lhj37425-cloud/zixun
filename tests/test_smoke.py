"""冒烟测试：确认项目骨架能被导入，命令入口能运行。"""

import daily_dissect
from daily_dissect import cli


def test_package_has_version():
    assert daily_dissect.__version__ == "0.1.0"


def test_cli_prints_help(capsys):
    assert cli.main([]) == 0
    assert "今日一拆" in capsys.readouterr().out
