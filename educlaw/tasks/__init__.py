"""
EduClaw 任务调度系统 — 心跳机制 (Heartbeat Task Engine)

支持两种任务类型:
  1. ScheduledTask — 定时任务: 按固定间隔自动调用智能体执行预设 prompt
  2. TriggerTask   — 触发任务: 条件满足时自动执行 (如学分不足触发预警)

用法:
  from educlaw.tasks import TaskManager, ScheduledTask, TriggerTask, CONDITION_REGISTRY

  tm = TaskManager()
  tm.add(ScheduledTask("每日问候", "早上好，请给我今天的学习建议", interval=3600))
  tm.add(TriggerTask("学分预警", "检测到学分不足，请生成预警",
         condition_id="credit_shortage", cooldown=86400))
  tm.start()
"""

import threading
import time
import json
import uuid
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Dict, List, Any, Optional


# ===== Condition Registry =====

def _check_credit_shortage() -> Optional[Dict[str, Any]]:
    """检查是否存在学分不足的学生 -> 返回触发上下文，否则 None"""
    from ..core.mock_data import COURSE_DATABASE
    from ..tools.warning import DEFAULT_RULES
    # 模拟检查学生数据
    student = {
        "name": "Demo User",
        "gpa": 3.12,
        "total_credits": 20.0,
        "required_credits": 140.0,
        "failed_courses": [],
    }
    gap = student["required_credits"] - student["total_credits"]
    if gap > 10:
        return {"student": student["name"], "reason": f"学分缺口 {gap:.0f} 分", "gap": gap}
    return None


def _check_low_gpa() -> Optional[Dict[str, Any]]:
    """检查 GPA 过低"""
    student = {
        "name": "Demo User",
        "gpa": 3.12,
    }
    if student["gpa"] < 2.5:
        return {"student": student["name"], "reason": f"GPA {student['gpa']:.2f} 低于 2.5", "gpa": student["gpa"]}
    return None


def _check_failed_courses() -> Optional[Dict[str, Any]]:
    """检查是否有挂科"""
    student = {
        "name": "Demo User",
        "failed": [],
    }
    if len(student["failed"]) > 0:
        return {"student": student["name"], "reason": f"{len(student['failed'])} 门挂科", "count": len(student["failed"])}
    return None


# 注册所有可用条件
CONDITION_REGISTRY: Dict[str, Callable[[], Optional[Dict[str, Any]]]] = {
    "credit_shortage": _check_credit_shortage,
    "low_gpa": _check_low_gpa,
    "failed_courses": _check_failed_courses,
}

CONDITION_DESC = {
    "credit_shortage": "学分不足预警 — 检测学分缺口超过10分时触发",
    "low_gpa": "GPA过低预警 — 检测GPA低于2.5时触发",
    "failed_courses": "挂科预警 — 检测有挂科记录时触发",
}


# ===== Task Models =====

class Task:
    def __init__(self, task_id: str, name: str, prompt: str, task_type: str,
                 interval: int = 0, condition_id: str = "", cooldown: int = 3600):
        self.task_id = task_id
        self.name = name
        self.prompt = prompt
        self.task_type = task_type  # "scheduled" or "trigger"
        self.interval = interval
        self.condition_id = condition_id
        self.cooldown = cooldown
        self.enabled = True

        self.created_at = datetime.now()
        self.last_run_at: Optional[datetime] = None
        self.next_run_at: Optional[datetime] = None
        self.execution_count = 0
        self.last_result: str = ""
        self.last_trigger_context: Optional[Dict] = None

    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "type": self.task_type,
            "prompt": self.prompt,
            "interval": self.interval,
            "condition_id": self.condition_id,
            "condition_desc": CONDITION_DESC.get(self.condition_id, ""),
            "cooldown": self.cooldown,
            "enabled": self.enabled,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "next_run_at": self.next_run_at.isoformat() if self.next_run_at else None,
            "execution_count": self.execution_count,
            "last_result": self.last_result[:200] if self.last_result else "",
        }

    def should_run(self, now: datetime) -> bool:
        if not self.enabled:
            return False

        if self.task_type == "scheduled":
            if self.next_run_at is None:
                self.next_run_at = now + timedelta(seconds=self.interval)
                return False
            return now >= self.next_run_at

        elif self.task_type == "trigger":
            if self.cooldown <= 0:
                return True
            if self.last_run_at is None:
                return True
            return (now - self.last_run_at).total_seconds() >= self.cooldown

        return False


def ScheduledTask(name: str, prompt: str, interval: int) -> Task:
    """创建定时任务 — 每隔 interval 秒自动执行一次"""
    return Task(
        task_id=str(uuid.uuid4())[:8],
        name=name,
        prompt=prompt,
        task_type="scheduled",
        interval=interval,
    )


def TriggerTask(name: str, prompt: str, condition_id: str, cooldown: int = 86400) -> Task:
    """创建触发任务 — 条件满足时自动执行，冷却 cooldown 秒"""
    return Task(
        task_id=str(uuid.uuid4())[:8],
        name=name,
        prompt=prompt,
        task_type="trigger",
        condition_id=condition_id,
        cooldown=cooldown,
    )


# ===== Task Manager =====

class TaskManager:
    """任务管理器 — 后台线程驱动定时/触发任务"""

    _instance: Optional["TaskManager"] = None

    def __init__(self, storage_path: str = "./data/tasks.json"):
        self._tasks: List[Task] = []
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._check_interval = 10  # 每10秒检查一次
        self._storage_path = Path(storage_path)
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._agent_factory: Optional[Callable] = None
        self._web_callbacks: List[Callable] = []
        self._log = []
        self._logger = logging.getLogger("tasks")

    @classmethod
    def get_instance(cls) -> "TaskManager":
        if cls._instance is None:
            cls._instance = TaskManager()
        return cls._instance

    def set_agent_factory(self, factory: Callable):
        """设置智能体工厂函数，用于执行任务"""
        self._agent_factory = factory

    def add_web_callback(self, callback: Callable):
        """添加 Web UI 回调 — 任务触发时推送到前端"""
        self._web_callbacks.append(callback)

    def add(self, task: Task) -> Task:
        """添加任务"""
        with self._lock:
            self._tasks.append(task)
            self._save()
            self._logger.info(f"Task added: [{task.task_type}] {task.name} ({task.task_id})")
        return task

    def remove(self, task_id: str) -> bool:
        """删除任务"""
        with self._lock:
            for t in self._tasks:
                if t.task_id == task_id:
                    self._tasks.remove(t)
                    self._save()
                    self._logger.info(f"Task removed: {t.name} ({task_id})")
                    return True
        return False

    def list_tasks(self) -> List[Dict]:
        """列出所有任务"""
        with self._lock:
            return [t.to_dict() for t in self._tasks]

    def get_log(self, limit: int = 20) -> List[Dict]:
        return self._log[-limit:]

    def start(self):
        """启动后台调度线程"""
        self._load()
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="task-scheduler")
        self._thread.start()
        self._logger.info(f"TaskManager started ({len(self._tasks)} tasks)")

    def stop(self):
        """停止后台调度"""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        self._logger.info("TaskManager stopped")

    def _run_loop(self):
        """后台主循环"""
        while not self._stop_event.wait(timeout=self._check_interval):
            self._tick()

    def _tick(self):
        """每 tick 检查是否有需要执行的任务"""
        now = datetime.now()
        with self._lock:
            tasks_to_run = [t for t in self._tasks if t.should_run(now)]

        for task in tasks_to_run:
            try:
                self._execute(task, now)
            except Exception as e:
                self._logger.error(f"Task execution failed: {task.name} — {e}")

    def _execute(self, task: Task, now: datetime):
        """执行一个任务"""
        # 触发类：先检查条件
        trigger_ctx = None
        if task.task_type == "trigger" and task.condition_id:
            cond_fn = CONDITION_REGISTRY.get(task.condition_id)
            if cond_fn:
                trigger_ctx = cond_fn()
                if trigger_ctx is None:
                    # 条件不满足，跳过（仍然更新 next 检查时间）
                    task.next_run_at = now + timedelta(seconds=max(task.cooldown, 60))
                    return

        # 格式化 prompt
        fmt_prompt = task.prompt
        if trigger_ctx:
            for k, v in trigger_ctx.items():
                fmt_prompt = fmt_prompt.replace(f"{{{k}}}", str(v))
            task.last_trigger_context = trigger_ctx

        self._logger.info(f"Executing task: [{task.task_type}] {task.name}")

        # 执行
        result_text = ""
        if self._agent_factory:
            try:
                import asyncio
                from agentscope.message import Msg

                agent = self._agent_factory()
                agent.memory.clear()

                resp = asyncio.run(agent(Msg("user", fmt_prompt, "user")))
                result_text = resp.get_text_content() if hasattr(resp, "get_text_content") else str(resp)
            except Exception as e:
                result_text = f"[LLM不可用] 任务触发: {task.name}\n\n条件上下文: {trigger_ctx}\n错误: {e}"
        else:
            result_text = f"[无Agent] 任务触发: {task.name}\n\nprompt: {fmt_prompt}\n上下文: {trigger_ctx}"

        # 更新状态
        task.last_run_at = now
        task.execution_count += 1
        task.last_result = result_text[:500]

        if task.task_type == "scheduled":
            task.next_run_at = now + timedelta(seconds=task.interval)
        else:
            task.next_run_at = now + timedelta(seconds=max(task.cooldown, 60))

        # 写入日志
        log_entry = {
            "time": now.isoformat(),
            "task_id": task.task_id,
            "task_name": task.name,
            "task_type": task.task_type,
            "result": result_text[:300],
            "trigger_context": trigger_ctx,
        }
        self._log.append(log_entry)
        if len(self._log) > 200:
            self._log = self._log[-200:]

        # 推送 Web UI 回调
        for cb in self._web_callbacks:
            try:
                cb(task.to_dict(), log_entry)
            except Exception:
                pass

        self._save()
        self._logger.info(f"Task done: {task.name} ({len(result_text)} chars)")

    def _save(self):
        """持久化到 JSON 文件"""
        try:
            data = {
                "tasks": [
                    {
                        "task_id": t.task_id,
                        "name": t.name,
                        "prompt": t.prompt,
                        "task_type": t.task_type,
                        "interval": t.interval,
                        "condition_id": t.condition_id,
                        "cooldown": t.cooldown,
                        "enabled": t.enabled,
                        "last_run_at": t.last_run_at.isoformat() if t.last_run_at else None,
                        "next_run_at": t.next_run_at.isoformat() if t.next_run_at else None,
                        "execution_count": t.execution_count,
                    }
                    for t in self._tasks
                ]
            }
            with open(self._storage_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self._logger.warning(f"Failed to save tasks: {e}")

    def _load(self):
        """从 JSON 文件恢复任务"""
        if not self._storage_path.exists():
            return
        try:
            with open(self._storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            with self._lock:
                for td in data.get("tasks", []):
                    task = Task(
                        task_id=td["task_id"],
                        name=td["name"],
                        prompt=td["prompt"],
                        task_type=td["task_type"],
                        interval=td.get("interval", 0),
                        condition_id=td.get("condition_id", ""),
                        cooldown=td.get("cooldown", 3600),
                    )
                    task.enabled = td.get("enabled", True)
                    if td.get("last_run_at"):
                        task.last_run_at = datetime.fromisoformat(td["last_run_at"])
                    if td.get("next_run_at"):
                        task.next_run_at = datetime.fromisoformat(td["next_run_at"])
                    task.execution_count = td.get("execution_count", 0)
                    self._tasks.append(task)
            self._logger.info(f"Loaded {len(self._tasks)} tasks from {self._storage_path}")
        except Exception as e:
            self._logger.warning(f"Failed to load tasks: {e}")
