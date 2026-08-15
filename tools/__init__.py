"""业务工具层。

本目录下的每个脚本都是一个「工具」：既可以被 Web 层作为 Python 模块导入，
也可以被 DeepSeek Harness 里的 Agent 通过 bash 命令独立执行（这是本项目工具调用的实现方式：
Agent 用 Harness 的持久 bash 工具执行 CLI，工具输出单行 JSON 便于模型解析）。

约定：
- 所有 CLI 输出单行 JSON（ensure_ascii=False，中文可读）；
- 出错时输出 {"error": "..."} 并以非零码退出，让 Agent 感知失败并自行重试；
- 每个脚本都与调用目录无关（路径按 __file__ 解析），因为 Agent 的工作目录是
  data/agent_workspace，而不是项目根目录。
"""
