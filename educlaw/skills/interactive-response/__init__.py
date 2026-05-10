"""交互式响应技能 — 指导智能体使用 <action> 标签生成可点击UI组件"""

from .scripts.tool import toolkit, run, parse_actions

skill_id = "interactive_response"
skill_name = "交互式响应"
skill_icon = "\U0001F3AF"
skill_desc = "生成可点击的选项按钮和输入框，让用户通过点击/输入继续对话"
