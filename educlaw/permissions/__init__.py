"""
EduClaw 权限控制系统 — CLI 控制权限 (类似 OpenClaw Permission System)

每个技能/操作有 4 种权限级别:
  - always_allow (0): 始终允许执行
  - ask_once     (1): 每次会话首次执行时询问用户确认
  - always_ask   (2): 每次执行都需要用户确认
  - deny         (3): 始终拒绝执行

用法:
  from educlaw.permissions import PermissionManager, PermissionLevel

  pm = PermissionManager()
  pm.check("course_search")         # -> True/False/needs_approval
  pm.approve_session("student_profile")  # 会话内记住授权
"""

import json
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Optional, Set

logger = logging.getLogger("permissions")


class PermissionLevel:
    ALWAYS_ALLOW = 0
    ASK_ONCE = 1
    ALWAYS_ASK = 2
    DENY = 3

    _names = {0: "always_allow", 1: "ask_once", 2: "always_ask", 3: "deny"}
    _cn = {0: "始终允许", 1: "问一次", 2: "每次都问", 3: "拒绝"}

    @classmethod
    def to_name(cls, level: int) -> str:
        return cls._names.get(level, "unknown")

    @classmethod
    def to_cn(cls, level: int) -> str:
        return cls._cn.get(level, "未知")

    @classmethod
    def from_name(cls, name: str) -> int:
        for k, v in cls._names.items():
            if v == name:
                return k
        return cls.ALWAYS_ALLOW


# 默认权限规则
DEFAULT_RULES = {
    "course_search":      PermissionLevel.ALWAYS_ALLOW,
    "course_recommend":   PermissionLevel.ALWAYS_ALLOW,
    "learning_path":      PermissionLevel.ALWAYS_ALLOW,
    "student_profile":    PermissionLevel.ASK_ONCE,      # 涉及学生数据
    "academic_warning":   PermissionLevel.ALWAYS_ASK,    # 涉及学业告警
    "task_create":        PermissionLevel.ASK_ONCE,
    "task_delete":        PermissionLevel.ALWAYS_ASK,
    "task_execute":       PermissionLevel.ALWAYS_ASK,
}


class PermissionManager:
    """权限管理器 — 检查/授权/拒绝操作"""

    _instance: Optional["PermissionManager"] = None

    def __init__(self, rules_path: str = "./data/permissions.json"):
        self._rules: Dict[str, int] = dict(DEFAULT_RULES)
        self._session_approved: Set[str] = set()
        self._pending: Dict[str, dict] = {}  # pending_id -> {action_id, context}
        self._rules_path = Path(rules_path)
        self._rules_path.parent.mkdir(parents=True, exist_ok=True)
        self._load_rules()

    @classmethod
    def get_instance(cls) -> "PermissionManager":
        if cls._instance is None:
            cls._instance = PermissionManager()
        return cls._instance

    def reset_session(self):
        """重置会话授权（新对话开始时调用）"""
        self._session_approved.clear()

    # ===== Rule Management =====

    def get_rule(self, action_id: str) -> int:
        return self._rules.get(action_id, PermissionLevel.ALWAYS_ALLOW)

    def set_rule(self, action_id: str, level: int):
        self._rules[action_id] = int(level)
        self._save_rules()

    def list_rules(self) -> dict:
        return {
            action_id: {
                "level": level,
                "level_name": PermissionLevel.to_name(level),
                "level_cn": PermissionLevel.to_cn(level),
            }
            for action_id, level in self._rules.items()
        }

    # ===== Permission Check =====

    def check(self, action_id: str, context: dict = None) -> dict:
        """
        检查操作是否需要权限。
        返回:
          {"status": "allowed" | "denied" | "ask", "action_id": ..., "pending_id": ...}

          allowed  - 可直接执行
          denied   - 被拒绝
          ask      - 需要用户确认 (pending_id 用于后续 approve/deny)
        """
        level = self.get_rule(action_id)

        if level == PermissionLevel.ALWAYS_ALLOW:
            return {"status": "allowed", "action_id": action_id}
        elif level == PermissionLevel.DENY:
            return {"status": "denied", "action_id": action_id}
        elif level == PermissionLevel.ASK_ONCE:
            if action_id in self._session_approved:
                return {"status": "allowed", "action_id": action_id}
            # Fall through to ask
        # ASK_ONCE first time or ALWAYS_ASK
        import uuid
        pid = str(uuid.uuid4())[:8]
        self._pending[pid] = {
            "action_id": action_id,
            "context": context or {},
            "level": level,
            "level_name": PermissionLevel.to_name(level),
        }
        return {"status": "ask", "action_id": action_id, "pending_id": pid}

    def approve(self, pending_id: str) -> dict:
        """用户批准待处理操作"""
        if pending_id not in self._pending:
            return {"status": "not_found"}
        item = self._pending.pop(pending_id)
        # 记住会话授权（对 ask_once 有效）
        if item["level"] == PermissionLevel.ASK_ONCE:
            self._session_approved.add(item["action_id"])
        logger.info(f"Permission approved: {item['action_id']} (level={item['level_name']})")
        return {"status": "approved", "action_id": item["action_id"]}

    def deny(self, pending_id: str) -> dict:
        """用户拒绝待处理操作"""
        item = self._pending.pop(pending_id, None)
        if item:
            logger.info(f"Permission denied: {item['action_id']}")
            return {"status": "denied", "action_id": item["action_id"]}
        return {"status": "not_found"}

    def get_pending(self, pending_id: str) -> Optional[dict]:
        return self._pending.get(pending_id)

    def clear_pending(self):
        self._pending.clear()

    # ===== Persistence =====

    def _load_rules(self):
        if not self._rules_path.exists():
            return
        try:
            with open(self._rules_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for action_id, level in data.get("rules", {}).items():
                self._rules[action_id] = int(level)
            logger.info(f"Loaded {len(self._rules)} permission rules")
        except Exception as e:
            logger.warning(f"Failed to load rules: {e}")

    def _save_rules(self):
        try:
            data = {"rules": self._rules}
            with open(self._rules_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save rules: {e}")
