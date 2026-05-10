from agentscope.tool import Toolkit, ToolResponse
from agentscope.message import TextBlock

from ....core.nl2sql import NL2SQLParser
from ....core.mock_data import COURSE_DATABASE
from ....models.course import Course

nl2sql = NL2SQLParser()


def _check_condition(course: Course, condition: str) -> bool:
    if "course_type" in condition:
        return course.course_type.value in condition
    if "difficulty" in condition:
        return course.difficulty.value in condition
    if "department" in condition:
        try:
            target_dept = condition.split("=")[1].strip().strip("'\"")
            return target_dept.lower() in course.department.lower()
        except (ValueError, IndexError):
            return False
    if "credit" in condition:
        try:
            target = float(condition.split("=")[1])
            return abs(course.credit - target) < 0.1
        except (ValueError, IndexError):
            return False
    return False


def _execute_search(keywords):
    results = []
    for course in COURSE_DATABASE.values():
        score = 0
        for kw in keywords:
            if kw.lower() in course.course_name.lower():
                score += 3
            if kw.lower() in course.description.lower():
                score += 2
            if kw.lower() in " ".join(course.attributes):
                score += 2
        for c in [k for k in keywords if "=" in k]:
            if _check_condition(course, c):
                score += 5
        if score > 0:
            results.append((course, score))
    results.sort(key=lambda x: x[1], reverse=True)
    return [c for c, _ in results]


def _format_results(courses, query):
    difficulty_map = {"easy": "简单", "medium": "中等", "hard": "困难"}
    type_map = {"required": "必修", "elective": "选修", "general": "通识"}
    lines = [f"找到 {len(courses)} 门与'{query}'相关的课程：", "=" * 50]
    for c in courses:
        lines.append(f"\n{c.course_name} ({c.course_id})")
        lines.append(f"   学分: {c.credit} | 课时: {c.hours}")
        lines.append(f"   类型: {type_map.get(c.course_type.value, '未知')}")
        lines.append(f"   难度: {difficulty_map.get(c.difficulty.value, '中等')}")
        lines.append(f"   院系: {c.department}")
        if c.prerequisites:
            lines.append(f"   先修: {', '.join(c.prerequisites)}")
        if c.attributes:
            lines.append(f"   标签: {', '.join(c.attributes)}")
        lines.append(f"   简介: {c.description}")
        if c.teachers:
            lines.append(f"   教师: {', '.join(c.teachers)}")
    return "\n".join(lines)


async def search_courses(query: str) -> ToolResponse:
    """搜索课程库，支持按关键词、难度级别、课程类型、院系等条件进行查询。当用户想找课程时使用此工具。"""
    keywords, _ = nl2sql.parse(query)
    results = _execute_search(keywords)
    if not results:
        return ToolResponse(content=[TextBlock(type="text", text=f"未找到与'{query}'相关的课程，建议尝试其他关键词。")])
    return ToolResponse(content=[TextBlock(type="text", text=_format_results(results, query))])


def run(prompt: str = "") -> str:
    from ..._async_compat import run_async
    result = run_async(search_courses(prompt or "编程"))
    if hasattr(result, "content") and result.content:
        block = result.content[0]
        return block.text if hasattr(block, "text") else block.get("text", str(block))
    return str(result)


toolkit = Toolkit()
toolkit.register_tool_function(search_courses)
