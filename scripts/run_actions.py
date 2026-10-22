"""Run the upstream sync without publishing book titles or note text in logs."""

import contextlib
import io
import re

from weread2notion.cli import main as sync_main


def main():
    output = io.StringIO()
    try:
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            sync_main(["sync"])
    except (Exception, SystemExit) as error:
        code = getattr(error, "code", "")
        code = str(getattr(code, "value", code))
        safe_code = code if re.fullmatch(r"[A-Za-z0-9_]{1,60}", code) else ""
        print(f"同步失败：{type(error).__name__} {safe_code}".rstrip())
        return 1
    count = sum(line.startswith("正在同步 ") for line in output.getvalue().splitlines())
    print(f"同步完成：本次处理 {count} 本书。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
