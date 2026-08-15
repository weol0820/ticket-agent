"""FastAPI Web 层：页面托管 + 工单接口 + Agent 调度入口。

设计说明：
- 前端保持零框架（原生 HTML/JS），重心放在 Agent 后端，避免炫技；
- POST /api/tickets 是“创建工单 → 交给 Agent 处理 → 返回结果”的一站式入口，
  处理是同步等待的（Agent 通常 30s-2min 完成），适合本地演示；
- 即使 Agent 失败（如未配密钥），工单也已在库中，补好配置后仍可查可重试。
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from agent.runner import agent
from tools import ticket_db

STATIC_DIR = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """应用生命周期：启动时建表，退出时回收 Harness 运行时子进程。"""
    ticket_db.init_db()
    yield
    agent.close()


app = FastAPI(title="智能客服工单处理 Agent", version="0.1.0", lifespan=lifespan)


class TicketIn(BaseModel):
    title: str
    description: str


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.post("/api/tickets")
def create_and_process(payload: TicketIn):
    """创建工单并交给 Agent 处理，返回处理结果（含写回库中的工单记录）。"""
    ticket = ticket_db.create_ticket(payload.title, payload.description)
    result = agent.process_ticket(ticket["id"], payload.title, payload.description)
    # 无论 ok 与否都返回 200，前端根据 ok 字段展示友好提示
    return result


@app.get("/api/tickets")
def list_tickets(limit: int = 50):
    return {"tickets": ticket_db.list_tickets(limit=limit)}


@app.get("/api/tickets/{ticket_id}")
def get_ticket(ticket_id: int):
    ticket = ticket_db.get_ticket(ticket_id)
    if ticket is None:
        return {"error": "工单不存在"}
    return ticket


@app.get("/api/health")
def health():
    return {"status": "ok"}
