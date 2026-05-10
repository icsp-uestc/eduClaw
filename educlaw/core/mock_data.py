"""
从 data/*.json 加载课程和学习路径数据。

迁移说明: 数据已从代码硬编码迁移到 data/ 目录的 JSON 文件。
  - data/courses.json      -> COURSE_DATABASE
  - data/learning-paths.json -> PATH_DATABASE
"""

from .data_loader import load_courses, load_paths
from ..models.course import Course, LearningPath, CourseType, Difficulty


def _build_courses(raw: dict) -> dict:
    """将 JSON 字典转换为 Course 对象字典。"""
    result = {}
    for cid, c in raw.items():
        result[cid] = Course(
            course_id=c["course_id"],
            course_name=c["course_name"],
            credit=float(c["credit"]),
            hours=int(c["hours"]),
            course_type=CourseType(c.get("course_type", "required")),
            department=c.get("department", ""),
            prerequisites=c.get("prerequisites", []),
            difficulty=Difficulty(c.get("difficulty", "medium")),
            attributes=c.get("attributes", []),
            description=c.get("description", ""),
            teachers=c.get("teachers", []),
        )
    return result


def _build_paths(raw: dict) -> dict:
    """将 JSON 字典转换为 LearningPath 对象字典。"""
    result = {}
    for pid, p in raw.items():
        result[pid] = LearningPath(
            path_id=p["path_id"],
            name=p["name"],
            target_abilities=p.get("target_abilities", []),
            semesters=p.get("semesters", []),
            total_credits=float(p.get("total_credits", 0)),
            estimated_duration=int(p.get("estimated_duration", 4)),
            description=p.get("description", ""),
        )
    return result


_raw_courses = load_courses()
_raw_paths = load_paths()

COURSE_DATABASE = _build_courses(_raw_courses) if _raw_courses else {}
PATH_DATABASE = _build_paths(_raw_paths) if _raw_paths else {}
