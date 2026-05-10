"""
EduClaw 用户认证模块 — 基于会话的登录系统。

当前登录用户存储在 Flask session 中。
所有技能通过 get_current_student() 获取当前用户数据。

支持两种模式：
  1. Flask Web 模式：从 session 中获取用户
  2. CLI/程序化模式：通过 set_current_user() 设置用户

安全原则：
  - 技能只能访问当前登录用户的数据
  - 禁止跨用户数据泄露
  - 默认用户为 "demo"
"""

try:
    from flask import session as _flask_session
except ImportError:
    _flask_session = None

from .data_loader import load_students

DEFAULT_USER_ID = "demo_user"
DEFAULT_USER_NAME = "Demo"

# 程序化上下文用户（CLI 模式下使用）
_context_user_id: str | None = None
_context_user_name: str | None = None

# 内置用户列表（从 students.json 加载）
_USERS: dict = {}


def _get_users() -> dict:
    global _USERS
    if not _USERS:
        _USERS = load_students()
    return _USERS


def set_current_user(user_id: str, user_name: str | None = None):
    """程序化设置当前用户（CLI 模式下使用）。"""
    global _context_user_id, _context_user_name
    _context_user_id = user_id
    _context_user_name = user_name


def clear_current_user():
    """清除程序化设置的用户。"""
    global _context_user_id, _context_user_name
    _context_user_id = None
    _context_user_name = None


def _safe_session_get(key: str, default=None):
    """安全获取 session 值，优先使用程序化上下文，无请求上下文时返回默认值。"""
    # 优先使用程序化上下文
    if key == "user_id" and _context_user_id is not None:
        return _context_user_id
    if key == "user_name" and _context_user_name is not None:
        return _context_user_name
    # 尝试 Flask session
    if _flask_session is not None:
        try:
            return _flask_session.get(key, default)
        except RuntimeError:
            pass
    return default


def login(student_id: str) -> dict | None:
    users = _get_users()
    user = users.get(student_id)
    if user is None:
        return None
    if _flask_session is not None:
        try:
            _flask_session["user_id"] = student_id
            _flask_session["user_name"] = user.get("name", student_id)
        except RuntimeError:
            pass  # Outside request context
    # 同时设置程序化上下文
    set_current_user(student_id, user.get("name", student_id))
    return {
        "student_id": student_id,
        "name": user.get("name", ""),
        "major": user.get("major", ""),
        "grade": user.get("grade", ""),
    }


def logout():
    clear_current_user()
    if _flask_session is not None:
        try:
            _flask_session.pop("user_id", None)
            _flask_session.pop("user_name", None)
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
    if _context_user_id is not None:
        return  # 程序化上下文已设置
    if _flask_session is not None:
        try:
            if "user_id" not in _flask_session:
                _flask_session["user_id"] = DEFAULT_USER_ID
                _flask_session["user_name"] = DEFAULT_USER_NAME
        except RuntimeError:
            pass  # Outside request context
