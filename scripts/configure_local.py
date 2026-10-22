"""Collect credentials locally without echoing secrets or starting a sync."""

import getpass
import os
from pathlib import Path
import re
import sys
import tempfile

from dotenv import dotenv_values


ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"


def main():
    if not sys.stdin.isatty():
        raise SystemExit("请在你自己的交互式终端运行；密钥不需要发到聊天里。")

    existing = dotenv_values(ENV_FILE) if ENV_FILE.exists() else {}
    prompts = [
        ("WEREAD_API_KEY", "微信读书 API Key", r"^[A-Za-z0-9._~+/=-]{10,}$"),
        ("NOTION_TOKEN", "Notion connection token", r"^(secret|ntn)_[A-Za-z0-9_-]{20,}$"),
        (
            "NOTION_PAGE",
            "你自己的 Notion 数据库链接或 ID",
            r"(?i)([a-f0-9]{32}|[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})",
        ),
    ]
    values = {}
    print("此命令只保存配置，不执行同步。已有值按回车保留。")
    for name, prompt, pattern in prompts:
        while True:
            read = input if name == "NOTION_PAGE" else getpass.getpass
            value = read(f"{prompt}: ").strip() or existing.get(name, "")
            if value and re.search(pattern, value) and not any(c in value for c in "\r\n'"):
                values[name] = value
                break
            print(f"{name} 为空或格式不正确，请重新输入。")

    if values["NOTION_PAGE"] == existing.get("NOTION_PAGE"):
        for name in ("NOTION_DATABASE_ID", "NOTION_DATA_SOURCE_ID"):
            if existing.get(name):
                values[name] = existing[name]

    fd, temporary = tempfile.mkstemp(prefix=".env-", dir=ROOT)
    try:
        with os.fdopen(fd, "w") as stream:
            stream.write("# 本地密钥文件；不要提交到 Git。\n")
            for name, value in values.items():
                stream.write(f"{name}='{value}'\n")
        os.replace(temporary, ENV_FILE)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    print(f"配置已保存到 {ENV_FILE}，权限为 0600。尚未执行同步。")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        raise SystemExit("\n已取消，原配置未修改。")
