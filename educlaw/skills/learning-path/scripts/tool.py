from agentscope.tool import Toolkit, ToolResponse
from agentscope.message import TextBlock

from ....core.mock_data import COURSE_DATABASE, PATH_DATABASE
from ....models.course import LearningPath


def _format_path(path: LearningPath) -> str:
    lines = [
        f"学习路径：{path.name}", "=" * 50,
        f"\n目标能力：{', '.join(path.target_abilities)}",
        f"预计时长：{path.estimated_duration} 个学期",
        f"总学分数：{path.total_credits}",
        f"\n描述：{path.description}",
        "\n学期安排：",
    ]
    for i, semester_courses in enumerate(path.semesters, 1):
        lines.append(f"\n第{i}学期：")
        for cid in semester_courses:
            if cid in COURSE_DATABASE:
                c = COURSE_DATABASE[cid]
                lines.append(f"  - {c.course_name} ({c.credit}学分)")
    return "\n".join(lines)


async def generate_learning_path(target: str) -> ToolResponse:
    """根据目标职业方向生成个性化学习路径，包含学期课程安排。当用户想规划学习路线时使用此工具。"""
    base_path = None
    for path in PATH_DATABASE.values():
        if target in path.name.lower():
            base_path = path
            break
    if not base_path:
        base_path = PATH_DATABASE["backend_dev"]
    return ToolResponse(content=[TextBlock(type="text", text=_format_path(base_path))])


def run(prompt: str = "") -> str:
    import asyncio
    result = asyncio.run(generate_learning_path(prompt or "后端开发工程师"))
    if hasattr(result, "content") and result.content:
        block = result.content[0]
        return block.text if hasattr(block, "text") else block.get("text", str(block))
    return str(result)


toolkit = Toolkit()
toolkit.register_tool_function(generate_learning_path)
