"""AgentService — 平台无关的 agent 调用服务，供 Web UI 和各 Bot Adapter 共用。"""

import asyncio
import logging
import os
import uuid
from datetime import datetime
from dataclasses import dataclass

from ..skills import discover_skills, list_skills, run_skill, get_skill
from ..core.auth import set_current_user, clear_current_user, get_current_student

logger = logging.getLogger("agent_service")


@dataclass
class ChatResponse:
    text: str
    chart_data: dict = None
    skill_id: str = None
    mode: str = "llm"  # "llm" | "direct" | "fallback"


def _run_async(coro):
    return asyncio.run(coro)


def _extract_agent_reply(response) -> str:
    if not hasattr(response, "content") or not response.content:
        return str(response)
    parts = []
    for block in response.content:
        t = block.get("text", "") if isinstance(block, dict) else getattr(block, "text", "")
        if isinstance(t, str) and t.strip():
            s = t.strip()
            if not s.startswith("{") or '"type"' not in s:
                parts.append(s)
    if not parts:
        return response.get_text_content() or str(response)
    return "\n\n".join(parts)


def _run_skill_sync(skill_id, prompt):
    result = run_skill(skill_id, prompt or "")
    if result is None:
        return "未知技能", None
    if isinstance(result, dict):
        return result.get("text", ""), result.get("chart_data")
    return result, None


class AgentService:
    def __init__(self, model_name: str = None, api_key: str = None, base_url: str = None):
        self.model_name = model_name or os.getenv("LLM_MODEL", "qwen2.5:7b")
        self.api_key = api_key or os.getenv("LLM_API_KEY", "EMPTY")
        self.base_url = base_url or os.getenv("LLM_API_BASE", "http://localhost:11434/v1")
        self.agent = None
        self.llm_available = False
        self.available_models = []
        self.last_error = ""
        self._conversations = {}
        self._conv_order = []

    def init_llm(self):
        from ..agents.edu_assistant import create_edu_agent
        if "localhost" in self.base_url or "127.0.0.1" in self.base_url:
            self.available_models = self._detect_local_models()
            if self.available_models:
                self.model_name = self.available_models[0]

        try:
            self.agent = create_edu_agent(
                model_name=self.model_name,
                api_key=self.api_key,
                base_url=self.base_url,
            )
            self.llm_available = True
            self.last_error = ""
            logger.info("LLM connected: %s @ %s", self.model_name, self.base_url)
        except Exception as e:
            self.agent = None
            self.llm_available = False
            self.last_error = str(e)
            logger.warning("LLM unavailable: %s", e)

    def _detect_local_models(self):
        if "localhost" not in self.base_url and "127.0.0.1" not in self.base_url:
            return []
        try:
            import httpx
            base = self.base_url.rstrip("/v1").rstrip("/") if "/v1" in self.base_url else self.base_url.rstrip("/")
            with httpx.Client(timeout=2) as c:
                r = c.get(f"{base}/api/tags")
                if r.status_code == 200:
                    return [m["name"] for m in r.json().get("models", [])]
        except Exception:
            pass
        return []

    def _smart_fallback(self, msg: str) -> str:
        msg_lower = msg.lower()
        if any(w in msg_lower for w in ["搜索", "找", "课程", "查", "有没有", "有哪些"]):
            return _run_skill_sync("course_search", msg)[0]
        if any(w in msg_lower for w in ["推荐", "建议", "适合"]):
            return _run_skill_sync("course_recommend", msg)[0]
        if any(w in msg_lower for w in ["路径", "规划", "计划", "安排", "后端", "前端", "全栈", "ai", "人工智能"]):
            return _run_skill_sync("learning_path", msg)[0]
        if any(w in msg_lower for w in ["画像", "能力", "成绩", "gpa", "水平"]):
            return _run_skill_sync("student_profile", msg)[0]
        if any(w in msg_lower for w in ["预警", "挂科", "警告", "风险", "学分"]):
            return _run_skill_sync("academic_warning", msg)[0]
        skills = list_skills()
        skill_lines = "\n".join(f"  - {s['name']}: {s['desc']}" for s in skills)
        return (
            "我是 EduClaw 教育伴学助手。\n\n"
            "当前 LLM 模型未连接，但我可以通过技能工具为你服务:\n"
            f"{skill_lines}\n\n"
            "请描述你的需求。"
        )

    def chat(self, user_id: str, message: str, skill_id: str = "",
             conv_id: str = "", user_name: str = "") -> ChatResponse:
        """统一聊天入口，同步包装。"""
        set_current_user(user_id, user_name or user_id)
        try:
            return self._chat_impl(user_id, message, skill_id, conv_id)
        finally:
            clear_current_user()

    def _chat_impl(self, user_id: str, message: str, skill_id: str,
                   conv_id: str) -> ChatResponse:
        skill_mod = get_skill(skill_id) if skill_id else None

        if self.llm_available and self.agent is not None:
            try:
                from agentscope.message import Msg
                chart_data = None
                if skill_mod:
                    _, chart_data = _run_skill_sync(skill_id, message)
                    prompt = f"请使用【{skill_mod.skill_name}】功能来回答以下问题。\n\n用户: {message or '请执行该功能'}"
                else:
                    prompt = message
                resp = _run_async(self.agent(Msg("user", prompt, "user")))
                content = _extract_agent_reply(resp)
                return ChatResponse(
                    text=content,
                    chart_data=chart_data,
                    skill_id=skill_id if skill_mod else None,
                    mode="llm",
                )
            except Exception as e:
                self.last_error = str(e)
                logger.warning("LLM call failed: %s", e)
                if skill_mod:
                    text, chart = _run_skill_sync(skill_id, message)
                    return ChatResponse(text=text, chart_data=chart, skill_id=skill_id, mode="direct")
                return ChatResponse(text=self._smart_fallback(message), mode="fallback")

        if skill_mod:
            text, chart = _run_skill_sync(skill_id, message)
            return ChatResponse(text=text, chart_data=chart, skill_id=skill_id, mode="direct")

        return ChatResponse(text=self._smart_fallback(message), mode="fallback")

    def clear_memory(self):
        if self.agent is not None:
            _run_async(self.agent.memory.clear())

    def test_llm(self) -> dict:
        if self.agent is None:
            return {"ok": False, "error": "Agent not initialized"}
        try:
            from agentscope.message import Msg
            _run_async(self.agent.memory.clear())
            resp = _run_async(self.agent(Msg("user", "回复 OK 即可，不要多说", "user")))
            content = _extract_agent_reply(resp)
            self.last_error = ""
            return {"ok": True, "reply": content[:100]}
        except Exception as e:
            self.last_error = str(e)
            self.llm_available = False
            return {"ok": False, "error": str(e)}

    # ---- Conversation management ----

    def create_conv(self) -> str:
        cid = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()
        self._conversations[cid] = {
            "id": cid, "title": "新对话", "messages": [],
            "created": now, "updated": now,
        }
        self._conv_order.append(cid)
        return cid

    def list_convs(self) -> list:
        return [
            {"id": cid, "title": c.get("title", "新对话"), "updated": c.get("updated", "")}
            for cid in reversed(self._conv_order) if self._conversations.get(cid)
        ]

    def get_conv(self, cid: str) -> dict:
        return self._conversations.get(cid)

    def delete_conv(self, cid: str) -> bool:
        if cid in self._conversations:
            del self._conversations[cid]
            if cid in self._conv_order:
                self._conv_order.remove(cid)
            return True
        return False
