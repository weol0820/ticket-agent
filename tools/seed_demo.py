"""初始化示例数据：建库 + 写入知识库条目与示例工单（幂等，可重复执行）。

运行：python tools/seed_demo.py
作用：
- 让项目 clone 下来后立刻有数据可看、可玩；
- 也是知识库条目的“配置文件”——业务方扩充 FAQ 时改这里的 DEFAULT_KB 即可。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import config  # noqa: E402
from tools import ticket_db  # noqa: E402

# ---------------------------------------------------------------------------
# 示例知识库：某电商平台的常见 FAQ（面试演示可替换为真实业务知识）
# ---------------------------------------------------------------------------
DEFAULT_KB = [
    {"id": "kb-001", "category": "退款", "tags": ["退款", "七天无理由", "到账时间"],
     "question": "订单退款多久到账？", "answer": "支持七天无理由退货的商品，退款在售后审核通过后 1-3 个工作日原路退回。"},
    {"id": "kb-002", "category": "物流", "tags": ["物流", "快递", "查询"],
     "question": "在哪里查询订单物流信息？", "answer": "登录后进入“我的订单-查看物流”；物流信息超过 48 小时未更新请联系售后物流组核实。"},
    {"id": "kb-003", "category": "账号", "tags": ["登录", "密码", "冻结"],
     "question": "账号无法登录怎么办？", "answer": "忘记密码可通过绑定手机验证码重置；账号冻结需提交实名信息走申诉流程，1 个工作日内审核。"},
    {"id": "kb-004", "category": "发票", "tags": ["发票", "报销"],
     "question": "如何开具电子发票？", "answer": "订单完成后在“订单详情-申请发票”提交抬头，电子发票 24 小时内发送至填写的邮箱。"},
    {"id": "kb-005", "category": "优惠券", "tags": ["优惠券", "满减", "叠加"],
     "question": "优惠券为什么无法使用？", "answer": "满减券不可与其他券叠加，且需满足券面门槛与有效期；部分特价/秒杀商品不参与用券。"},
    {"id": "kb-006", "category": "售后", "tags": ["质量问题", "换货", "证据"],
     "question": "商品有质量问题怎么处理？", "answer": "请在订单详情提交质量问题售后申请并上传照片/视频证据，售后 24 小时内审核，支持换货或退款。"},
    {"id": "kb-007", "category": "支付", "tags": ["支付失败", "重复扣款", "退款"],
     "question": "付款成功但订单显示未支付？", "answer": "请先核对支付渠道扣款记录；确属重复扣款的，系统会在对账后自动原路退回，一般 1-3 个工作日到账。"},
    {"id": "kb-008", "category": "会员", "tags": ["VIP", "权益"],
     "question": "VIP 会员有哪些权益？", "answer": "会员享专属价、优先客服通道与每月 3 次免运费券，权益明细见“会员中心-我的权益”。"},
    {"id": "kb-009", "category": "投诉", "tags": ["投诉", "时效", "响应"],
     "question": "投诉多久能得到处理？", "answer": "一般投诉 24 小时内响应，3 个工作日内给出处理方案；涉及资金安全的投诉优先处理。"},
    {"id": "kb-010", "category": "订单", "tags": ["取消订单", "拒收"],
     "question": "下单后如何取消订单？", "answer": "未发货订单可在“我的订单”自助取消；已发货订单需拒收后申请退款，运费按平台规则承担。"},
]

# ---------------------------------------------------------------------------
# 示例工单：覆盖典型业务场景（咨询/售后/故障/投诉）
# ---------------------------------------------------------------------------
DEFAULT_TICKETS = [
    ("付款成功但订单显示未支付", "我在 20:15 用银行卡付款成功，银行已经扣款，但订单页面一直显示待支付，请尽快帮我核实。", "web"),
    ("买的衣服尺码不合适想退货", "上周买的连衣裙 M 码偏小，标签还在，想申请七天无理由退货，请问怎么操作？", "app"),
    ("账号被冻结无法下单", "登录时提示账号存在风险被冻结，我什么都没做，现在无法下单，请马上处理。", "web"),
    ("优惠券下单时提示不满足条件", "我有两张满 200 减 50 的券，下单 400 元的商品却提示不满足使用条件，是什么原因？", "app"),
]


def seed() -> dict:
    """写入示例数据，返回统计信息。"""
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    ticket_db.init_db()

    if config.KB_FILE.exists():
        kb_count = len(json.loads(config.KB_FILE.read_text(encoding="utf-8")))
    else:
        config.KB_FILE.write_text(json.dumps(DEFAULT_KB, ensure_ascii=False, indent=2),
                                  encoding="utf-8")
        kb_count = len(DEFAULT_KB)

    existing = ticket_db.list_tickets(limit=1000)
    created = 0
    if not existing:  # 只在空库时写入，避免重复
        for title, desc, channel in DEFAULT_TICKETS:
            ticket_db.create_ticket(title, desc, channel)
            created += 1
    return {"kb_entries": kb_count, "tickets_created": created,
            "tickets_total": len(existing) + created,
            "ticket_db": str(config.TICKET_DB), "kb_file": str(config.KB_FILE)}


if __name__ == "__main__":
    print(json.dumps(seed(), ensure_ascii=False, indent=2))
