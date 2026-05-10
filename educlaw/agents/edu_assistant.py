"""EduClaw Agent — 基于 AgentScope ReActAgent 的教育伴学智能体"""

from agentscope.agent import ReActAgent
from agentscope.formatter import OpenAIChatFormatter
from agentscope.memory import InMemoryMemory
from agentscope.model import OpenAIChatModel
from agentscope.tool import Toolkit

from ..skills import discover_skills, register_toolkits, list_skills

SYS_PROMPT_TEMPLATE = """你是一个教育伴学智能助手，名叫 EduClaw（教育之爪）。

你提供的核心服务：
{skill_list}

【内置能力 — 交互式回复格式】
当需要用户选择或输入时，使用以下标签。前端会自动渲染为按钮/输入框。

**关键规则：**
- <action> 标签本身就是回复内容，不要在外面用文字重复罗列同样的选项。
- 在 <action> 前只写一到两句引导语。
- 如果用了 <action>，禁止再重复写一个纯文本的选项列表或表格。

select 格式（用户点击选项按钮）：
<action type="select" id="唯一ID">
| 值 | 名称 | 说明 |
|----|------|------|
</action>

input 格式（用户填写输入框）：
<action type="input" id="唯一ID" prompt="提示">
</action>

【当前用户】
学生: {student_name} (ID: {student_id})
专业: {student_major} / 年级: {student_grade}

【隐私原则】只能查询和展示当前登录用户的信息，禁止泄露其他用户的数据。

工作原则：
- 需要查询数据时调用相应工具函数，工具会自动获取当前用户的数据。
- 推荐课程、展示选项时使用 <action type="select"> 让用户点击。
- 需要额外信息时使用 <action type="input"> 提供输入框。
- 友好语气，清晰结构，简洁有实质。"""


def _build_sys_prompt() -> str:
    skills = list_skills()
    lines = []
    for s in skills:
        if s["id"] == "interactive_response":
            continue  # Built-in, not listed
        lines.append(f"{len(lines)+1}. **{s['name']}** — {s['desc']}")

    # Get current user context
    from ..core.auth import get_current_student
    student = get_current_student()
    return SYS_PROMPT_TEMPLATE.format(
        skill_list="\n".join(lines),
        student_name=student.get("name", "Demo"),
        student_id=student.get("student_id", "demo_user"),
        student_major=student.get("major", "未知"),
        student_grade=student.get("grade", "未知"),
    )


def create_edu_agent(
    model_name: str = "gpt-4o-mini",
    api_key: str = "EMPTY",
    base_url: str = "http://localhost:11434/v1",
    temperature: float = 0.7,
) -> ReActAgent:
    """创建 EduClaw Agent"""
    generate_kwargs = {"temperature": temperature}

    # DeepSeek thinking mode conflicts with ReActAgent multi-turn:
    # AgentScope formatter strips thinking blocks, but DeepSeek API requires
    # reasoning_content to be passed back on continuation, causing 400 errors.
    # Disable thinking for ReActAgent; re-enable when AgentScope supports it.
    is_deepseek = "deepseek" in base_url.lower()
    if is_deepseek:
        generate_kwargs["extra_body"] = {"thinking": {"type": "disabled"}}

    model = OpenAIChatModel(
        model_name=model_name,
        api_key=api_key,
        stream=False,
        client_kwargs={"base_url": base_url, "timeout": 120},
        generate_kwargs=generate_kwargs,
    )

    formatter = OpenAIChatFormatter()
    toolkit = Toolkit()
    register_toolkits(toolkit)

    agent = ReActAgent(
        name="EduClaw助手",
        sys_prompt=_build_sys_prompt(),
        model=model,
        formatter=formatter,
        toolkit=toolkit,
        memory=InMemoryMemory(),
        max_iters=20,
    )

    return agent
