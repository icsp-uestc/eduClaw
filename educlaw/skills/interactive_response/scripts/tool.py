"""交互式响应工具 — 指导智能体使用 <action> 标签格式化可交互回复"""

from agentscope.tool import Toolkit, ToolResponse
from agentscope.message import TextBlock

import re


def parse_actions(text: str) -> list:
    """从文本中提取所有 <action> 块"""
    pattern = r'<action\s+(.*?)>(.*?)</action>'
    actions = []
    for m in re.finditer(pattern, text, re.DOTALL):
        attrs_str = m.group(1)
        body = m.group(2).strip()
        attrs = {}
        for am in re.finditer(r'(\w+)="([^"]*)"', attrs_str):
            attrs[am.group(1)] = am.group(2)

        action = {"type": attrs.get("type", ""), "id": attrs.get("id", ""), "body": body}
        if action["type"] == "input":
            action["prompt"] = attrs.get("prompt", "请输入")
        elif action["type"] == "select":
            action["options"] = _parse_table(body)

        actions.append(action)

    # Strip action blocks from text
    clean_text = re.sub(pattern, '', text, flags=re.DOTALL).strip()
    return clean_text.strip(), actions


def _parse_table(text: str) -> list:
    """解析 markdown 表格为选项列表"""
    lines = [l.strip() for l in text.strip().split('\n') if l.strip() and not l.strip().startswith('|-')]
    if len(lines) < 2:
        return []
    headers = [h.strip() for h in lines[0].strip('| ').split('|')]
    options = []
    for line in lines[1:]:
        cells = [c.strip() for c in line.strip('| ').split('|')]
        if len(cells) >= 2:
            option = {"value": cells[0]}
            for i, h in enumerate(headers[1:], 1):
                if i < len(cells):
                    option[h] = cells[i]
            options.append(option)
    return options


async def format_interactive_response(template: str) -> ToolResponse:
    """使用 <action> 标签生成交互式回复。当需要用户选择或输入时使用此工具格式化输出。

    支持两种标签:
      <action type="select" id="xxx">表格</action>  — 可点击的选项按钮
      <action type="input" id="xxx" prompt="提示"> — 输入框

    表格格式: | 选项 | 列1 | 列2 |  (第一列为选项值)
    """
    return ToolResponse(content=[TextBlock(type="text", text=template)])


def run(prompt: str = ""):
    return f"""当需要用户选择或补充信息时，请在回复中使用 <action> 标签：

<action type="select" id="唯一ID">
| 选项 | 名称 | 说明 |
|------|------|------|
</action>

或

<action type="input" id="唯一ID" prompt="提示文字">
</action>"""


toolkit = Toolkit()
toolkit.register_tool_function(format_interactive_response)
