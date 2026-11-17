"""项目里各个文件夹的位置。

默认按这个文件所在的位置推算项目根目录。设置环境变量 DD_ROOT 可以换成别的目录。
"""

import os
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("DD_ROOT") or PACKAGE_DIR.parents[1])

CONTENT_DIR = ROOT / "content"
SITE_DIR = ROOT / "site"
CONFIG_DIR = ROOT / "config"
SOURCES_FILE = CONFIG_DIR / "sources.toml"
DATA_DIR = ROOT / "data"
POOL_FILE = DATA_DIR / "pool.json"
PROMPTS_DIR = ROOT / "prompts"

WEB_DIR = PACKAGE_DIR / "web"
TEMPLATES_DIR = WEB_DIR / "templates"
STATIC_DIR = WEB_DIR / "static"
