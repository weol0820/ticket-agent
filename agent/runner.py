"""Agent 运行器：封装 DeepSeek Harness Python SDK。

设计要点（与官方 SDK 用法一致）：
1. 同一个 DeepSeekHarness 实例长期复用（内部运行时子进程延迟启动、跨任务保持存活），
   应用关闭时显式 close() 回收子进程。
2. 每条工单使用独立 session_id：会话（含 bash 状态）互不污染，
   同时 JSONL 会话日志按工单归档在 data/sessions/，事后可审计 Agent 的完整工具调用链。
3. 系统提示词通过 env 注入（DSH_SYSTEM_PROMPT → cordis.yml 的 persona），
   任务提示词里携带本机绝对路径，Agent 才能用 bash 调到业务工具。
4. “以数据库为准”：Agent 结论最终以 tools/ticket_update.py 写回的工单记录为权威结果，
   LLM 最终文本仅用于前端展示与容错比对。
"""

from __future__ import annotations

import json
import re
import sys
import uuid
from pathlib import Path

from deepseek_harness import DeepSeekHarness

import config
from agent.prompts import SYSTEM_PROMPT, build_task_prompt

# Agent 通过 bash 调用业务工具所需的绝对路径信息（避免把用户机器路径写死在提示词里）
TOOLS_DIR = str((config.PROJECT_ROOT / "tools").resolve())
PYTHON_BIN = sys.executable


def _extract_json(text: str) -> dict | None:
    """从模型最终输出中提取 JSON 对象。

    模型可能把 JSON 包在 ```json ... ``` 代码块里，或前后附少量说明文字，
    这里做容错解析：优先整体解析，再尝试提取首个 JSON 对象片段。
    """
    text = (text or "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if fence:
        try:
            return json.loads(fence.group(1))
        except json.JSONDecodeError:
            pass
    brace = re.search(r"\{.*\}", text, re.S)
    if brace:
        try:
            return json.loads(brace.group(0))
        except json.JSONDecodeError:
            pass
    return None


class TicketAgent:
    """客服工单 Agent 门面：Web 层只跟它打交道，不感知 Harness 细节。"""

    def __init__(self) -> None:
        self._harness: DeepSeekHarness | None = None

    def _ensure(self) -> DeepSeekHarness:
        """惰性创建（并复用）harness 运行时。"""
        if self._harness is None:
            config.AGENT_WORKSPACE.mkdir(parents=True, exist_ok=True)
            config.SESSION_ROOT.mkdir(parents=True, exist_ok=True)

            # 注入运行时子进程的环境变量：凭据 + 端点 + 系统提示词
            env_extra: dict[str, str] = {"DSH_SYSTEM_PROMPT": SYSTEM_PROMPT}
            if config.DEEPSEEK_API_KEY:
                env_extra["DEEPSEEK_API_KEY"] = config.DEEPSEEK_API_KEY
            if config.DEEPSEEK_BASE_URL:
                env_extra["DEEPSEEK_BASE_URL"] = config.DEEPSEEK_BASE_URL

            self._harness = DeepSeekHarness(
                provider="deepseek-official",
                model=config.DSH_MODEL,
                max_tokens=config.DSH_MAX_TOKENS,
                cwd=str(config.AGENT_WORKSPACE),   # Agent 的隔离工作目录
                session_root=str(config.SESSION_ROOT),  # 会话 JSONL 日志目录
                cordis=str(config.CORDIS_CONFIG),  # 本项目自带的运行时组合
                env=env_extra,
            )
        return self._harness

    def process_ticket(self, ticket_id: int, title: str, description: str) -> dict:
        """让 Agent 处理一条工单，返回结构化结果（供前端展示）。

        返回：
            {
              "ok": bool, "message": str,
              "agent_json": dict|None,     # 模型输出的结构化结论（容错解析）
              "agent_text": str,           # 模型最终原文
              "ticket": dict|None,         # 写回数据库后的工单记录（权威结果）
              "session_id": str,           # 会话 id，对应 data/sessions/ 下的审计日志
              "finish_reason": str|None,
            }
        """
        if not config.DEEPSEEK_API_KEY:
            return {"ok": False,
                    "message": "未配置 DEEPSEEK_API_KEY：请复制 .env.example 为 .env 并填写密钥。"
                               "（不想调用大模型可先运行 python demo_tools.py 体验工具链）"}

        session_id = f"ticket-{ticket_id}-{uuid.uuid4().hex[:8]}"
        prompt = build_task_prompt(ticket_id, title, description, TOOLS_DIR, PYTHON_BIN)
        try:
            result = self._ensure().run(prompt, session_id=session_id)
        except Exception as exc:  # 网络、密钥、运行时启动等异常统一兜底
            return {"ok": False, "message": f"Agent 运行失败：{exc}", "session_id": session_id}

        agent_json = _extract_json(result.final_response)

        # 权威结果：从数据库读回该工单（Agent 应已通过 ticket_update 落库）
        from tools import ticket_db  # 局部导入，保持模块依赖清晰
        ticket = ticket_db.get_ticket(ticket_id)

        if ticket is None or (ticket.get("category") is None and ticket.get("priority") is None):
            note = ("Agent 未成功写回工单库（可能工具调用失败），"
                    f"finish_reason={result.finish_reason}。会话日志见 data/sessions/{session_id}.jsonl")
            return {"ok": False, "message": note, "agent_json": agent_json,
                    "agent_text": result.final_response, "ticket": ticket,
                    "session_id": session_id, "finish_reason": result.finish_reason}

        return {"ok": True, "message": "处理完成，结论已写回工单库。",
                "agent_json": agent_json, "agent_text": result.final_response,
                "ticket": ticket, "session_id": session_id,
                "finish_reason": result.finish_reason}

    def close(self) -> None:
        """应用退出时回收运行时子进程（FastAPI lifespan 调用）。"""
        if self._harness is not None:
            self._harness.close()
            self._harness = None


# Web 层共用的单例
agent = TicketAgent()
