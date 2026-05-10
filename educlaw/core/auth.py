"""
EduClaw 用户认证模块 — 基于会话的登录系统。

当前登录用户存储在 Flask session 中。
所有技能通过 get_current_student() 获取当前用户数据。

安全原则：
  - 技能只能访问当前登录用户的数据
  - 禁止跨用户数据泄露
  - 默认用户为 "demo"
"""

from flask import session
from .data_loader import load_students

DEFAULT_USER_ID = "demo_user"
DEFAULT_USER_NAME = "Demo"

# 内置用户列表（从 students.json 加载）
_USERS: dict = {}


def _get_users() -> dict:
    global _USERS
    if not _USERS:
        _USERS = load_students()
    return _USERS


def _safe_session_get(key: str, default=None):
    """安全获取 session 值，无请求上下文时返回默认值"""
    try:
        return session.get(key, default)
    except RuntimeError:
        return default


def login(student_id: str) -> dict | None:
    users = _get_users()
    user = users.get(student_id)
    if user is None:
        return None
    try:
        session["user_id"] = student_id
        session["user_name"] = user.get("name", student_id)
    except RuntimeError:
        pass  # Outside request context, just return user info
    return {
        "student_id": student_id,
        "name": user.get("name", ""),
        "major": user.get("major", ""),
        "grade": user.get("grade", ""),
    }


def logout():
    try:
        session.pop("user_id", None)
        session.pop("user_name", None)
    except RuntimeError:
        pass


def get_current_user_id() -> str:
    return _safe_session_get("user_id", DEFAULT_USER_ID)


def get_current_user_name() -> str:
    return _safe_session_get("user_name", DEFAULT_USER_NAME)


def is_logged_in() -> bool:
    return bool(_safe_session_get("user_id", None))


def get_current_student() -> dict:
    """获取当前登录用户的完整数据，无会话时返回 demo"""
    uid = get_current_user_id()
    users = _get_users()
    return users.get(uid) or users.get(DEFAULT_USER_ID, {
        "student_id": DEFAULT_USER_ID,
        "name": DEFAULT_USER_NAME,
        "major": "计算机科学与技术",
        "grade": "大二",
        "gpa": 3.0,
        "total_credits": 0,
        "required_credits": 140,
        "grade_records": [],
    })


def get_available_users() -> list:
    """获取所有可用用户列表（不含敏感数据）"""
    users = _get_users()
    return [{"student_id": uid, "name": u["name"]} for uid, u in users.items()]


def ensure_login():
    """确保有用户登录，否则自动登录 demo"""
    try:
        if "user_id" not in session:
            session["user_id"] = DEFAULT_USER_ID
            session["user_name"] = DEFAULT_USER_NAME
    except RuntimeError:
        pass  # Outside request context
