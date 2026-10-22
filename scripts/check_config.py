"""Check both accounts and the database schema without changing remote data."""

import logging
import os
from pathlib import Path

import requests
from dotenv import load_dotenv
from notion_client import Client
from notion_client.errors import APIResponseError

from weread2notion import cli


ROOT = Path(__file__).resolve().parents[1]


def main():
    load_dotenv(ROOT / ".env", override=True)
    missing = [name for name in ("WEREAD_API_KEY", "NOTION_TOKEN") if not os.getenv(name)]
    if not any(os.getenv(name) for name in ("NOTION_PAGE", "NOTION_DATABASE_ID", "NOTION_DATA_SOURCE_ID")):
        missing.append("NOTION_PAGE（自己的数据库链接）")
    if missing:
        print("尚未完成配置，缺少：" + "、".join(missing))
        print(f"请填写 {ROOT / '.env'}，或运行 scripts/configure_local.py。")
        return 2

    try:
        secrets = cli.validate_secret_inputs()
    except cli.ConfigError:
        return 2

    try:
        response = requests.post(
            cli.WEREAD_GATEWAY_URL,
            headers={"Authorization": f"Bearer {secrets['weread_api_key']}"},
            json={"api_name": "/user/notebooks", "skill_version": cli.WEREAD_SKILL_VERSION, "count": 1},
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("upgrade_info"):
            print("微信读书要求升级接口版本，请先检查上游更新。")
            return 1
        if data.get("errcode", 0) != 0:
            print(f"微信读书验证失败，错误码：{data.get('errcode')}。请检查 API Key。")
            return 1
        if "books" not in data:
            print("微信读书响应结构不符，未执行同步。")
            return 1
        print("微信读书：账号读取成功。")
    except requests.HTTPError as error:
        print(f"微信读书：HTTP {error.response.status_code}，请检查密钥和网络。")
        return 1
    except (requests.RequestException, ValueError):
        print("微信读书：网络请求失败或响应不是有效 JSON。")
        return 1

    cli.client = Client(auth=secrets["notion_token"], notion_version=cli.NOTION_VERSION,
                        log_level=logging.ERROR, timeout_ms=15000)
    try:
        cli.data_source_id = cli.resolve_data_source_id(cli.extract_notion_id())
        cli.load_data_source_schema()
        cli.build_equals_filter("BookId", "0")
        cli.get_sort()
        print("Notion：数据库读取、BookId 和 Sort 字段检查通过。")
    except APIResponseError as error:
        code = getattr(error.code, "value", error.code)
        print(f"Notion 验证失败（{code}）。请检查 token、数据库链接和连接的页面访问权限。")
        return 1
    except Exception as error:
        print(f"Notion 数据库检查失败（{type(error).__name__}）。请检查数据库模板和网络。")
        return 1
    finally:
        cli.client.close()
    print("只读检查通过，尚未导入或删除任何笔记。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
