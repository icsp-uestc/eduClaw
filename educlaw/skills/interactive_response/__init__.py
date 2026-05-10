"""交互式响应技能 — 指导智能体使用 <action> 标签生成可点击UI组件

这是一个纯文档型技能（prompt-only），不注册工具函数到 Toolkit，
仅通过 SKILL.md 为 LLM 提供格式化指导。
"""

from .scripts.tool import parse_actions

skill_id = "interactive_response"
skill_name = "交互式响应"
skill_icon = "\U0001F3AF"
skill_desc = "生成可点击的选项按钮和输入框，让用户通过点击/输入继续对话"

# 标记为 prompt-only skill，不注册空壳工具
is_prompt_only = True

# 提供空 toolkit 以兼容 register_toolkits
from agentscope.tool import Toolkit
toolkit = Toolkit()


def run(prompt: str = ""):
    """返回使用说明（纯文本）。"""
    return """当需要用户选择或补充信息时，请在回复中使用 <action> 标签：

<action type="select" id="唯一ID">
| 选项 | 名称 | 说明 |
|------|------|------|
</action>

或

<action type="input" id="唯一ID" prompt="提示文字">
</action>"""
