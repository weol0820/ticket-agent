"""离线工具演示：不调用大模型，直接体验完整业务工具链。

运行：python demo_tools.py

适用场景：
- 还没申请 DeepSeek API Key 时验证环境是否装好；
- 面试/答辩时演示数据层与知识库检索效果（零成本、秒级出结果）；
- 排查“Agent 调不到工具”类问题时，先用本脚本确认工具本身正常。

说明：本脚本只读不写（不修改工单库），写库操作由 Agent 或
tools/ticket_update.py 完成，可自行尝试：
    python tools/ticket_update.py --id 1 --category 咨询 --priority 3 \
        --assignee 售前咨询组 --reply "测试答复" --reason "演示写库"
"""

from __future__ import annotations

import json

from tools import kb, ticket_db
from tools.seed_demo import seed


def main() -> None:
    print("=" * 60)
    print("步骤 1/3：初始化示例数据（建库 + 知识库 + 示例工单）")
    print("=" * 60)
    print(json.dumps(seed(), ensure_ascii=False, indent=2))

    print("\n" + "=" * 60)
    print("步骤 2/3：查询工单库（Agent 的 ticket_query 工具同款逻辑）")
    print("=" * 60)
    tickets = ticket_db.list_tickets(limit=5)
    for t in tickets:
        print(f"[{t['id']}] {t['title']}  (status={t['status']}, category={t['category']})")

    print("\n" + "=" * 60)
    print("步骤 3/3：知识库检索（Agent 的 kb_search 工具同款逻辑）")
    print("=" * 60)
    if tickets:
        demo_query = tickets[0]["title"] + " " + tickets[0]["description"]
        hits = kb.search_kb(demo_query)
        for h in hits:
            print(f"  {h['id']}  [{h['category']}] 得分={h['score']}")
            print(f"    问：{h['question']}")
            print(f"    答：{h['answer']}")
        if not hits:
            print("  （无命中条目）")

    print("\n工具链验证完成 —— 配置 .env 中的 DEEPSEEK_API_KEY 后，运行 python run.py 体验完整 Agent。")


if __name__ == "__main__":
    main()
