"""一键启动 Web 服务。

用法：
    python run.py
然后浏览器打开 http://127.0.0.1:8000

启动前请确认：
1. python tools/seed_demo.py   已初始化示例数据；
2. .env 已配置 DEEPSEEK_API_KEY（未配置也能打开页面，但提交工单会提示先配密钥）。
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run("web.app:app", host="127.0.0.1", port=8000)
