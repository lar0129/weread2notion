"""Validate local configuration, upload Actions secrets and start the first sync."""

import json
import os
import subprocess
import sys

import check_config


REPOSITORY = "lar0129/weread2notion"
UPSTREAM = "malinkang/weread2notion"
WORKFLOW = "weread.yml"


def gh(arguments, label, secret=None):
    try:
        result = subprocess.run(
            ["gh", *arguments],
            input=secret,
            text=True,
            capture_output=True,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired):
        raise RuntimeError(f"{label}失败，请检查 gh 登录状态和网络。") from None
    if result.returncode:
        # Never print command inputs or server error bodies containing credentials.
        raise RuntimeError(f"{label}失败（退出码 {result.returncode}），尚未确认同步启动。")
    return result.stdout


def main():
    result = check_config.main()
    if result:
        return result

    repository = json.loads(gh(["api", f"repos/{REPOSITORY}"], "检查 GitHub 仓库"))
    if repository.get("full_name") != REPOSITORY or (repository.get("parent") or {}).get("full_name") != UPSTREAM:
        raise RuntimeError("仓库身份与预期 Fork 不符，未上传密钥。")

    names = ("WEREAD_API_KEY", "NOTION_TOKEN", "NOTION_PAGE", "NOTION_DATABASE_ID", "NOTION_DATA_SOURCE_ID")
    existing = json.loads(gh(["secret", "list", "--repo", REPOSITORY, "--json", "name"], "读取密钥名称"))
    existing_names = {item["name"] for item in existing}
    # Do not silently keep an older destination that overrides the new database.
    stale = [name for name in names[2:] if name in existing_names and not os.getenv(name)]
    if stale:
        raise RuntimeError("GitHub 存在本地未配置的旧目标字段：" + "、".join(stale) + "。请先核对目标数据库。")

    for name in names:
        value = os.getenv(name)
        if value:
            gh(["secret", "set", name, "--repo", REPOSITORY], f"保存 {name}", secret=value)
            print(f"GitHub Actions Secret 已保存：{name}")

    gh(["api", "--method", "PUT", f"repos/{REPOSITORY}/actions/permissions", "-F", "enabled=true"], "启用仓库 Actions")
    workflow_path = f"repos/{REPOSITORY}/actions/workflows/{WORKFLOW}"
    gh(["api", "--method", "PUT", f"{workflow_path}/enable"], "启用同步工作流")
    gh(["api", "--method", "POST", f"{workflow_path}/dispatches", "-f", "ref=main"], "启动首次同步")
    print(f"已请求首次同步；运行结果请查看 https://github.com/{REPOSITORY}/actions")
    print("定时任务：每天北京时间 08:00；GitHub 排队可能导致延迟。")
    print("注意：同步的书籍页面会被上游重建，请在其他 Notion 页面整理个人补充笔记。")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
