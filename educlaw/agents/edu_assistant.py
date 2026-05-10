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

工作原则：
- 当用户的问题需要查询数据或执行操作时，优先调用相应的工具函数。
- 用友好的语气回复，使用清晰的结构化格式展示信息。
- 如果用户没有明确提供学生ID等信息，使用 demo_user 作为默认值。
- 回答简洁但有实质性内容，不要过度冗长。"""


def _build_sys_prompt() -> str:
    skills = list_skills()
    lines = []
    for i, s in enumerate(skills, 1):
        lines.append(f"{i}. **{s['name']}** — {s['desc']}")
    return SYS_PROMPT_TEMPLATE.format(skill_list="\n".join(lines))


def create_edu_agent(
    model_name: str = "gpt-4o-mini",
    api_key: str = "EMPTY",
    base_url: str = "http://localhost:11434/v1",
    temperature: float = 0.7,
) -> ReActAgent:
    """创建 EduClaw Agent"""
    model = OpenAIChatModel(
        model_name=model_name,
        api_key=api_key,
        stream=False,
        client_kwargs={"base_url": base_url, "timeout": 120},
        generate_kwargs={"temperature": temperature},
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
        max_iters=10,
    )

    return agent
