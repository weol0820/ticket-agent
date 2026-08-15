"""工具：知识库检索（供 Agent 通过 bash 调用）。

用法示例：
    python tools/kb_search.py "订单已付款但显示未支付 重复扣款"
    python tools/kb_search.py "衣服尺码不合适想退货" --top 3

输出：单行 JSON，含每条命中条目的 id / 得分 / 内容。
Agent 在“建议答复”中必须引用命中的条目 id，保证答复有据可查。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import config  # noqa: E402
from tools import kb  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="知识库检索")
    parser.add_argument("query", help="查询文本（主题 + 关键故障词效果最好）")
    parser.add_argument("--top", type=int, default=config.KB_TOP_K, help="返回条数")
    args = parser.parse_args()

    try:
        hits = kb.search_kb(args.query, top_k=args.top)
        print(json.dumps({"count": len(hits), "hits": hits}, ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
