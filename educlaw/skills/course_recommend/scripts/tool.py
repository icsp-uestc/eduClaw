from agentscope.tool import Toolkit, ToolResponse
from agentscope.message import TextBlock

from ....core.nl2sql import NL2SQLParser
from ....core.mock_data import COURSE_DATABASE

nl2sql = NL2SQLParser()


async def recommend_courses(query: str = "", limit: int = 5) -> ToolResponse:
    """基于用户输入的需求推荐课程列表。当用户请求推荐课程时使用此工具。"""
    all_courses = list(COURSE_DATABASE.values())
    keywords, _ = nl2sql.parse(query)
    scored = []
    for course in all_courses:
        score = 0
        for kw in keywords:
            if kw.lower() in course.course_name.lower():
                score += 2
            if kw.lower() in " ".join(course.attributes):
                score += 1
        if score > 0 or not keywords:
            scored.append((course, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    courses = [c for c, _ in scored[:limit]]
    if not courses:
        text = "未找到匹配的课程推荐。"
    else:
        lines = ["为您推荐以下课程：", "=" * 50]
        for i, c in enumerate(courses, 1):
            lines.append(f"\n{i}. {c.course_name} ({c.course_id})")
            lines.append(f"   学分: {c.credit} | 难度: {c.difficulty.value}")
            if c.description:
                lines.append(f"   {c.description}")
        text = "\n".join(lines)
    return ToolResponse(content=[TextBlock(type="text", text=text)])


def run(prompt: str = "") -> str:
    from ..._async_compat import run_async
    result = run_async(recommend_courses(prompt or "", 5))
    if hasattr(result, "content") and result.content:
        block = result.content[0]
        return block.text if hasattr(block, "text") else block.get("text", str(block))
    return str(result)


toolkit = Toolkit()
toolkit.register_tool_function(recommend_courses)
