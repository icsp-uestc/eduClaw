"""飞书消息 → 飞书卡片 JSON 构建器。

将 AgentService 返回的 ChatResponse 转换为飞书消息格式。
支持：Markdown 文本卡片、交互按钮卡片。
"""

import re


def parse_actions(text: str) -> tuple:
    """从文本中提取 <action> 标签，返回 (clean_text, actions_list)。"""
    actions = []
    regex = re.compile(r'<action\s+(.*?)>([\s\S]*?)</action>', re.DOTALL)

    for m in regex.finditer(text):
        attrs_str = m.group(1)
        body = m.group(2).strip()
        attrs = {}
        for am in re.finditer(r'(\w+)="([^"]*)"', attrs_str):
            attrs[am.group(1)] = am.group(2)
        action = {"type": attrs.get("type", ""), "id": attrs.get("id", ""), "body": body}
        if action["type"] == "input":
            action["prompt"] = attrs.get("prompt", "请输入")
        elif action["type"] == "select":
            action["options"] = _parse_markdown_table(body)
        actions.append(action)

    clean = regex.sub("", text).strip()
    return clean, actions


def _parse_markdown_table(text: str) -> list:
    """将 markdown 表格解析为 [{value, name, desc}, ...]。"""
    lines = [l.strip() for l in text.split('\n') if l.strip() and not l.strip().startswith('|-')]
    if len(lines) < 2:
        return []
    headers = [h.strip() for h in lines[0].strip('|').split('|')]
    opts = []
    for line in lines[1:]:
        cells = [c.strip() for c in line.strip('|').split('|')]
        if len(cells) >= 2:
            opt = {"value": cells[0]}
            for i, h in enumerate(headers[1:], 1):
                if i < len(cells):
                    opt[h] = cells[i]
            opts.append(opt)
    return opts


def _escape_markdown(text: str) -> str:
    """转义飞书 Markdown 特殊字符。"""
    return text.replace("\\", "\\\\").replace("*", "\\*").replace("_", "\\_")


def build_feishu_message(text: str, chart_data: dict = None) -> dict:
    """将 agent 回复文本转换为飞书消息 JSON。

    优先使用交互式卡片（含 action 按钮），纯文本则用 Markdown 消息。
    返回: {"msg_type": "interactive"|"text", "content": ...}
    """
    clean_text, actions = parse_actions(text)

    # 移除 markdown 中的 HTML 标签残留
    clean_text = re.sub(r'<br\s*/?>', '\n', clean_text)
    clean_text = re.sub(r'<[^>]+>', '', clean_text)

    if actions:
        return _build_card(clean_text, actions)
    return _build_text(clean_text)


def _build_text(text: str) -> dict:
    """纯文本消息。"""
    return {
        "msg_type": "text",
        "content": json_dumps({"text": text}),
    }


def _build_card(clean_text: str, actions: list) -> dict:
    """构建飞书交互式卡片消息。"""
    card = {
        "config": {"wide_screen_mode": True},
        "elements": [],
    }

    if clean_text:
        # 飞书卡片 markdown 有长度限制，截断过长的文本
        markdown_text = clean_text[:4000]
        card["elements"].append({
            "tag": "markdown",
            "content": markdown_text,
        })

    for action in actions:
        if action["type"] == "select" and action.get("options"):
            # 飞书按钮最多 4 个一组
            buttons = []
            for opt in action["options"][:10]:
                label = opt.get("名称") or opt.get("课程") or opt.get("选项") or opt.get("value", "")
                desc = opt.get("说明") or opt.get("难度") or ""
                if desc and len(label) + len(desc) < 40:
                    label = f"{label} ({desc})"
                buttons.append({
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": label[:40]},
                    "value": opt.get("value", ""),
                    "type": "default",
                })
            if buttons:
                groups = [buttons[i:i+4] for i in range(0, len(buttons), 4)]
                for group in groups:
                    card["elements"].append({"tag": "action", "actions": group})

        elif action["type"] == "input":
            card["elements"].append({
                "tag": "action",
                "actions": [{
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": action.get("prompt", "请输入")},
                    "value": action.get("id", ""),
                    "type": "primary",
                }],
            })

    # 确保卡片不为空
    if not card["elements"]:
        card["elements"].append({
            "tag": "markdown",
            "content": clean_text[:4000] if clean_text else "请查看回复内容",
        })

    return {
        "msg_type": "interactive",
        "content": json_dumps(card),
    }


def json_dumps(obj) -> str:
    """JSON 序列化，避免引入额外依赖。"""
    import json
    return json.dumps(obj, ensure_ascii=False)
