"""工单数据层：SQLite 封装。

职责：建表、创建工单、查询工单、白名单更新工单。
Agent 通过 tools/ticket_update.py 写入这里；Web 层直接读取这里展示。
“以数据库为准”——Agent 的结论只有落到这张表里才算数。
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS tickets (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT    NOT NULL,                -- 工单标题
    description     TEXT    NOT NULL,                -- 工单内容（用户原始描述）
    channel         TEXT    DEFAULT 'web',           -- 来源渠道：web/phone/email
    category        TEXT,                            -- 分类：咨询/故障/投诉/售后/其他
    priority        INTEGER,                         -- 优先级 1-10，>=8 建议升级
    status          TEXT    DEFAULT 'open',          -- open/processing/resolved/escalated
    assignee_group  TEXT,                            -- 建议分派组
    suggested_reply TEXT,                            -- Agent 生成的建议答复
    agent_reason    TEXT,                            -- Agent 决策理由（含知识库引用）
    created_at      TEXT,
    updated_at      TEXT
);
"""

# 可被更新工具修改的字段白名单（防止 Agent 改写 id / 创建时间等）
UPDATABLE_FIELDS = {"category", "priority", "status", "assignee_group",
                    "suggested_reply", "agent_reason"}


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_conn() -> sqlite3.Connection:
    """获取连接；SQLite 单文件库，关闭即落盘。"""
    conn = sqlite3.connect(config.TICKET_DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """建表（幂等）。"""
    with get_conn() as conn:
        conn.execute(SCHEMA)


def create_ticket(title: str, description: str, channel: str = "web") -> dict:
    """新建一条待处理工单，返回完整记录。

    注意：insert 后必须先 commit，再用新连接读取——
    否则读到的可能是未提交前的旧状态（返回 None）。
    """
    init_db()
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO tickets (title, description, channel, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (title, description, channel, _now(), _now()),
        )
        ticket_id = cur.lastrowid
        conn.commit()  # 显式提交，保证随后 get_ticket 的新连接能读到该行
    return get_ticket(ticket_id)


def get_ticket(ticket_id: int) -> dict | None:
    init_db()
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    return dict(row) if row else None


def list_tickets(status: str | None = None, keyword: str | None = None,
                 limit: int = 50) -> list[dict]:
    """按条件列出工单（供 Web 列表页与 ticket_query 工具共用）。"""
    init_db()
    sql, params = "SELECT * FROM tickets WHERE 1=1", []
    if status:
        sql += " AND status = ?"
        params.append(status)
    if keyword:
        sql += " AND (title LIKE ? OR description LIKE ?)"
        params += [f"%{keyword}%", f"%{keyword}%"]
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def update_ticket(ticket_id: int, **fields) -> dict | None:
    """白名单更新工单字段。

    规则：
    - 只允许更新 UPDATABLE_FIELDS 中的字段（其余一律拒绝，防止越权改写）；
    - category/status 必须在 config 定义的合法取值内；
    - priority 必须是 1-10 的整数。
    """
    if get_ticket(ticket_id) is None:
        raise ValueError(f"工单 {ticket_id} 不存在")

    cleaned: dict = {}
    for key, value in fields.items():
        if value is None:
            continue
        if key not in UPDATABLE_FIELDS:
            raise ValueError(f"字段 {key} 不允许更新（白名单：{sorted(UPDATABLE_FIELDS)}）")
        if key == "category" and value not in config.TICKET_CATEGORIES:
            raise ValueError(f"分类必须是 {sorted(config.TICKET_CATEGORIES)} 之一，收到：{value}")
        if key == "status" and value not in config.TICKET_STATUSES:
            raise ValueError(f"状态必须是 {sorted(config.TICKET_STATUSES)} 之一，收到：{value}")
        if key == "assignee_group" and value not in config.ASSIGNEE_GROUPS:
            raise ValueError(f"分派组必须是 {sorted(config.ASSIGNEE_GROUPS)} 之一，收到：{value}")
        if key == "priority":
            value = int(value)
            if not 1 <= value <= 10:
                raise ValueError(f"优先级必须是 1-10 的整数，收到：{value}")
        cleaned[key] = value

    if not cleaned:
        return get_ticket(ticket_id)

    assignments = ", ".join(f"{k} = ?" for k in cleaned)
    with get_conn() as conn:
        conn.execute(
            f"UPDATE tickets SET {assignments}, updated_at = ? WHERE id = ?",
            (*cleaned.values(), _now(), ticket_id),
        )
    return get_ticket(ticket_id)
