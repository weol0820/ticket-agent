"""全局配置：读取 .env，集中管理环境变量与路径。

设计说明：所有可能变化的量（密钥、模型、阈值、路径）都收敛到这里，
业务代码不散落魔法值，新人接手或部署迁移时只需改 .env 或本文件。
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# 项目根目录（本文件所在目录）
PROJECT_ROOT = Path(__file__).resolve().parent

# 优先读取项目根目录 .env；不存在时静默跳过（配置均有默认值兜底）
load_dotenv(PROJECT_ROOT / ".env")

# ---------------------------------------------------------------------------
# 路径配置
# ---------------------------------------------------------------------------
DATA_DIR = PROJECT_ROOT / "data"                       # 数据根目录
TICKET_DB = DATA_DIR / "tickets.db"                    # SQLite 工单库
KB_FILE = DATA_DIR / "knowledge_base.json"             # 知识库（FAQ 条目）
AGENT_WORKSPACE = DATA_DIR / "agent_workspace"         # Agent 隔离工作目录（Harness 的 cwd）
SESSION_ROOT = DATA_DIR / "sessions"                   # Harness 会话 JSONL 日志（可审计 Agent 的工具调用过程）
CORDIS_CONFIG = PROJECT_ROOT / "agent" / "cordis.yml"  # Harness 运行时组合配置

# ---------------------------------------------------------------------------
# 模型相关（与 DeepSeek Harness Python SDK 对齐）
# 参考：https://github.com/deepseek-ai/deepseek-harness/blob/master/docs/user/guide/python-sdk.md
# ---------------------------------------------------------------------------
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
# 留空 = 使用官方公开端点 https://api.deepseek.com；如有 OpenAI 兼容代理可覆盖
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "")
# 模型 id 由你的 API 端点决定：公开端点可用 deepseek-chat / deepseek-reasoner，
# 也可改为端点支持的其它 id（如 deepseek-v4-flash）
DSH_MODEL = os.getenv("DSH_MODEL", "deepseek-chat")
DSH_MAX_TOKENS = int(os.getenv("DSH_MAX_TOKENS", "8192"))

# ---------------------------------------------------------------------------
# 业务阈值
# ---------------------------------------------------------------------------
KB_TOP_K = int(os.getenv("KB_TOP_K", "3"))             # 知识库检索返回条数
ESCALATE_SCORE = int(os.getenv("ESCALATE_SCORE", "8"))  # 优先级 >= 该值的工单建议升级

# 工单状态机（写库白名单，防止 Agent 写入非法状态）
TICKET_STATUSES = {"open", "processing", "resolved", "escalated"}
TICKET_CATEGORIES = {"咨询", "故障", "投诉", "售后", "其他"}
ASSIGNEE_GROUPS = {"售前咨询组", "技术支持组", "投诉处理组", "售后物流组", "账务组"}
