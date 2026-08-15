"""一键启动 Web 服务。

用法：
    python run.py
然后浏览器打开 http://127.0.0.1:8000

启动前请确认：
1. python tools/seed_demo.py   已初始化示例数据；
2. .env 已配置 DEEPSEEK_API_KEY（未配置也能打开页面，但提交工单会提示先配密钥）。
"""

import os

import uvicorn

if __name__ == "__main__":
    # 支持环境变量覆盖：WSL2/容器场景可 APP_HOST=0.0.0.0 对外暴露
    host = os.getenv("APP_HOST", "127.0.0.1")
    port = int(os.getenv("APP_PORT", "8000"))
    uvicorn.run("web.app:app", host=host, port=port)
