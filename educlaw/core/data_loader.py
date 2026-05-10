"""
EduClaw 数据加载器 — 从 data/ 目录读取 JSON 数据文件。

所有数据文件:
  data/courses.json         — 课程数据库
  data/learning-paths.json  — 学习路径
  data/students.json        — 学生档案及成绩
  data/warning-rules.json   — 预警规则

用法:
  from educlaw.core.data_loader import load_courses, load_paths, load_students, load_warning_rules
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("data_loader")

DATA_DIR = Path(__file__).parent.parent.parent / "data"

_cache: Dict[str, Any] = {}


def _load_json(filename: str) -> Optional[Dict[str, Any]]:
    """加载 JSON 文件（带缓存）。"""
    if filename in _cache:
        return _cache[filename]
    filepath = DATA_DIR / filename
    if not filepath.exists():
        logger.warning(f"Data file not found: {filepath}")
        return None
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        _cache[filename] = data
        return data
    except Exception as e:
        logger.error(f"Failed to load {filename}: {e}")
        return None


def load_courses() -> Dict[str, Any]:
    return _load_json("courses.json") or {}


def load_paths() -> Dict[str, Any]:
    return _load_json("learning-paths.json") or {}


def load_students() -> Dict[str, Any]:
    return _load_json("students.json") or {}


def load_warning_rules() -> Dict[str, Any]:
    return _load_json("warning-rules.json") or {}


def get_student(student_id: str) -> Optional[Dict[str, Any]]:
    return load_students().get(student_id)


def get_course(course_id: str) -> Optional[Dict[str, Any]]:
    return load_courses().get(course_id)


def get_path(path_id: str) -> Optional[Dict[str, Any]]:
    return load_paths().get(path_id)


def clear_cache():
    """清除缓存（重新加载时使用）。"""
    _cache.clear()
