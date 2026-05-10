from typing import List, Tuple, Optional, Dict, Any

from agentscope.tool import Toolkit, ToolResponse
from agentscope.message import TextBlock

from ..models.course import Course, LearningPath
from ..core.nl2sql import NL2SQLParser
from ..core.mock_data import COURSE_DATABASE, PATH_DATABASE

nl2sql = NL2SQLParser()


def _check_condition(course: Course, condition: str) -> bool:
    if "course_type" in condition:
        return course.course_type.value in condition
    if "difficulty" in condition:
        return course.difficulty.value in condition
    if "credit" in condition:
        try:
            target = float(condition.split("=")[1])
            return abs(course.credit - target) < 0.1
        except (ValueError, IndexError):
            return False
    return False


def _execute_search(keywords: List[str]) -> List[Course]:
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
        conditions = [k for k in keywords if "=" in k]
        for c in conditions:
            if _check_condition(course, c):
                score += 5
        if score > 0:
            results.append((course, score))
    results.sort(key=lambda x: x[1], reverse=True)
    return [c for c, _ in results]


def _format_course_results(courses: List[Course], query: str) -> str:
    difficulty_map = {"easy": "简单", "medium": "中等", "hard": "困难"}
    type_map = {"required": "必修", "elective": "选修", "general": "通识"}
    lines = [f"找到 {len(courses)} 门与'{query}'相关的课程：", "=" * 50]
    for course in courses:
        lines.append(f"\n{course.course_name} ({course.course_id})")
        lines.append(f"   学分: {course.credit} | 课时: {course.hours}")
        lines.append(f"   类型: {type_map.get(course.course_type.value, '未知')}")
        lines.append(f"   难度: {difficulty_map.get(course.difficulty.value, '中等')}")
        lines.append(f"   院系: {course.department}")
        if course.prerequisites:
            lines.append(f"   先修: {', '.join(course.prerequisites)}")
        if course.attributes:
            lines.append(f"   标签: {', '.join(course.attributes)}")
        lines.append(f"   简介: {course.description}")
        if course.teachers:
            lines.append(f"   教师: {', '.join(course.teachers)}")
    return "\n".join(lines)


def _format_path(path: LearningPath) -> str:
    lines = [
        f"学习路径：{path.name}",
        "=" * 50,
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


async def search_courses(query: str) -> ToolResponse:
    """搜索课程库，支持按关键词、难度级别、课程类型、院系等条件进行查询。当用户想找课程时使用此工具。"""
    keywords, intent = nl2sql.parse(query)
    results = _execute_search(keywords)
    if not results:
        return ToolResponse(content=[
            TextBlock(type="text", text=f"未找到与'{query}'相关的课程，建议尝试其他关键词。")
        ])
    text = _format_course_results(results, query)
    return ToolResponse(content=[TextBlock(type="text", text=text)])


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


async def generate_learning_path(target: str) -> ToolResponse:
    """根据目标职业方向生成个性化学习路径，包含学期课程安排。当用户想规划学习路线时使用此工具。"""
    base_path = None
    for path in PATH_DATABASE.values():
        if target in path.name.lower():
            base_path = path
            break
    if not base_path:
        base_path = PATH_DATABASE["backend_dev"]

    text = _format_path(base_path)
    return ToolResponse(content=[TextBlock(type="text", text=text)])


course_toolkit = Toolkit()
course_toolkit.register_tool_function(search_courses)
course_toolkit.register_tool_function(recommend_courses)
course_toolkit.register_tool_function(generate_learning_path)
