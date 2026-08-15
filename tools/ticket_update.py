"""工具：更新工单（供 Agent 通过 bash 调用）。

用法示例：
    python tools/ticket_update.py --id 3 --category 故障 --priority 8 \
        --assignee 技术支持组 --reply "建议转人工并核实重复扣款" --reason "涉及资金安全，kb-007 提到重复扣款自动退回，需人工核实"

输出：更新后的完整工单记录（单行 JSON）。
安全设计：字段白名单 + 取值校验在 tools/ticket_db.update_ticket 里完成，
Agent 只能改允许改的字段、写允许写的取值。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools import ticket_db  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="更新工单（白名单字段）")
    parser.add_argument("--id", type=int, required=True, help="工单 id（必填）")
    parser.add_argument("--category", help="分类：咨询/故障/投诉/售后/其他")
    parser.add_argument("--priority", type=int, help="优先级 1-10（>=8 建议升级）")
    parser.add_argument("--status", help="状态：open/processing/resolved/escalated")
    parser.add_argument("--assignee", help="建议分派组")
    parser.add_argument("--reply", help="建议答复（基于知识库改写，不编造）")
    parser.add_argument("--reason", help="决策理由（2-3 句，引用知识库条目 id）")
    args = parser.parse_args()

    try:
        fields = {
            "category": args.category,
            "priority": args.priority,
            "status": args.status,
            "assignee_group": args.assignee,
            "suggested_reply": args.reply,
            "agent_reason": args.reason,
        }
        ticket = ticket_db.update_ticket(args.id, **fields)
        print(json.dumps(ticket, ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
