"""工具：查询工单库（供 Agent 通过 bash 调用）。

用法示例：
    python tools/ticket_query.py --id 3
    python tools/ticket_query.py --status open
    python tools/ticket_query.py --keyword 退款 --limit 5

输出：单行 JSON（便于模型解析）。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# 保证从任意工作目录（包括 Agent 的 data/agent_workspace）调用都能导入项目模块
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools import ticket_db  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="查询工单库")
    parser.add_argument("--id", type=int, help="按工单 id 精确查询")
    parser.add_argument("--status", help="按状态过滤：open/processing/resolved/escalated")
    parser.add_argument("--keyword", help="按标题/内容关键字模糊查询")
    parser.add_argument("--limit", type=int, default=10, help="最多返回条数（默认 10）")
    args = parser.parse_args()

    try:
        if args.id is not None:
            ticket = ticket_db.get_ticket(args.id)
            if ticket is None:
                print(json.dumps({"error": f"工单 {args.id} 不存在"}, ensure_ascii=False))
                sys.exit(1)
            result = {"count": 1, "tickets": [ticket]}
        else:
            tickets = ticket_db.list_tickets(status=args.status, keyword=args.keyword,
                                             limit=args.limit)
            result = {"count": len(tickets), "tickets": tickets}
        print(json.dumps(result, ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
