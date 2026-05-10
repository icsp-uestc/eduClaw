import asyncio
import os
import uuid
import logging
from datetime import datetime

from flask import Flask, render_template, request, jsonify

from ..skills import discover_skills, list_skills, run_skill as _run_skill_by_id, get_skill
from ..tasks import TaskManager, ScheduledTask, TriggerTask, CONDITION_REGISTRY, CONDITION_DESC
from ..permissions import PermissionManager, PermissionLevel

app = Flask(__name__, template_folder="templates", static_folder="static")

conversations = {}
conversation_order = []

_agent = None
_agent_model = None
_agent_url = None
_llm_available = False
_available_models = []


def _run_async(coro):
    return asyncio.run(coro)


def _extract_text(result):
    if hasattr(result, "content") and result.content:
        block = result.content[0]
        if hasattr(block, "text"):
            return block.text
        if isinstance(block, dict):
            return block.get("text", str(block))
    return str(result)


def _run_skill(skill_id, prompt):
    result = _run_skill_by_id(skill_id, prompt)
    if result is None:
        return "未知技能: " + skill_id, None
    if isinstance(result, dict):
        return result.get("text", ""), result.get("chart_data")
    return result, None


def _init_llm():
    """Auto-detect models and try to create agent on startup."""
    global _agent, _agent_model, _agent_url, _llm_available, _available_models
    try:
        _available_models = _detect_models()
        default_model = _available_models[0] if _available_models else os.getenv("LLM_MODEL", "qwen2.5:7b")
        default_url = os.getenv("LLM_API_BASE", "http://localhost:11434/v1")
        default_key = os.getenv("LLM_API_KEY", "EMPTY")
        _create_agent(default_model, default_key, default_url)
    except Exception:
        pass


def _detect_models():
    try:
        import httpx
        url = os.getenv("LLM_API_BASE", "http://localhost:11434/v1")
        if "/v1" in url:
            base = url.rstrip("/v1").rstrip("/")
        else:
            base = url.rstrip("/")
        with httpx.Client(timeout=3) as client:
            r = client.get(f"{base}/api/tags")
            if r.status_code == 200:
                return [m["name"] for m in r.json().get("models", [])]
    except Exception:
        pass
    return []


def _create_agent(model_name, api_key, base_url):
    global _agent, _agent_model, _agent_url, _llm_available
    from ..agents.edu_assistant import create_edu_agent
    try:
        _agent = create_edu_agent(model_name=model_name, api_key=api_key, base_url=base_url)
        _agent_model = model_name
        _agent_url = base_url
        _llm_available = True
        logging.getLogger("web").info(f"LLM connected: {model_name} @ {base_url}")
    except Exception as e:
        _agent = None
        _llm_available = False
        logging.getLogger("web").warning(f"LLM unavailable: {e}")


def _smart_fallback(msg):
    """When LLM is unavailable, try to match the message to a skill."""
    msg_lower = msg.lower()
    if any(w in msg_lower for w in ["搜索", "找", "课程", "查", "有没有", "有哪些"]):
        return _run_skill("course_search", msg)
    if any(w in msg_lower for w in ["推荐", "建议", "适合"]):
        return _run_skill("course_recommend", msg)
    if any(w in msg_lower for w in ["路径", "规划", "计划", "安排", "后端", "前端", "全栈", "ai", "人工智能"]):
        return _run_skill("learning_path", msg)
    if any(w in msg_lower for w in ["画像", "能力", "成绩", "gpa", "水平"]):
        return _run_skill("student_profile", msg)
    if any(w in msg_lower for w in ["预警", "挂科", "警告", "风险", "学分"]):
        return _run_skill("academic_warning", msg)
    skills = list_skills()
    skill_lines = "\n".join(f"  - {s['name']}：{s['desc']}" for s in skills)
    return (
        "我是 EduClaw 教育伴学助手。\n\n"
        "当前 LLM 模型未连接，但我可以通过技能工具为你服务：\n"
        f"{skill_lines}\n\n"
        "请在输入栏左侧的扳手图标中选择一项技能，或直接描述你的需求。"
    )


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/skills")
def api_skills():
    return jsonify({"ok": True, "data": {s["id"]: s for s in list_skills()}})


@app.route("/api/status")
def api_status():
    return jsonify({
        "ok": True,
        "data": {
            "llm_available": _llm_available,
            "model": _agent_model,
            "url": _agent_url,
            "available_models": _available_models,
        }
    })


@app.route("/api/chat", methods=["POST"])
def api_chat():
    body = request.get_json(force=True)
    msg = body.get("message", "").strip()
    skill_id = body.get("skill", "")
    conv_id = body.get("conv_id", "")

    if not msg and not skill_id:
        return jsonify({"ok": False, "error": "Empty message"})

    skill_mod = get_skill(skill_id) if skill_id else None
    pm = getattr(app, '_permission_manager', None) or PermissionManager.get_instance()

    # Permission check for skill-based actions
    if skill_id:
        perm = pm.check(skill_id, {"message": msg})
        if perm["status"] == "denied":
            return jsonify({"ok": True, "data": f"操作已被权限系统拒绝。\n\n技能「{skill_mod.skill_name if skill_mod else skill_id}」当前权限级别为「拒绝」，无法执行。请联系管理员修改权限设置。"})
        if perm["status"] == "ask":
            return jsonify({
                "ok": True,
                "needs_permission": True,
                "pending_id": perm["pending_id"],
                "action_id": skill_id,
                "action_name": skill_mod.skill_name if skill_mod else skill_id,
                "action_desc": skill_mod.skill_desc if skill_mod else "",
                "data": f"需要您的确认才能执行「{skill_mod.skill_name if skill_mod else skill_id}」操作。\n\n{skill_mod.skill_desc if skill_mod else ''}",
            })

    if _llm_available and _agent is not None:
        try:
            from agentscope.message import Msg
            _run_async(_agent.memory.clear())
            chart_data = None
            if skill_mod:
                _, chart_data = _run_skill(skill_id, msg)
                prompt = f"请使用【{skill_mod.skill_name}】功能来回答以下问题。\n\n用户：{msg or '请执行该功能'}"
            else:
                prompt = msg
            resp = _run_async(_agent(Msg("user", prompt, "user")))
            content = resp.get_text_content() if hasattr(resp, "get_text_content") else str(resp)
            result = {"ok": True, "data": content, "skill": (skill_id if skill_mod else None)}
            if chart_data:
                result["chart_data"] = chart_data
            return jsonify(result)
        except Exception:
            if skill_mod:
                text, chart = _run_skill(skill_id, msg)
                result = {"ok": True, "data": text, "skill": skill_id}
                if chart:
                    result["chart_data"] = chart
                return jsonify(result)
            result = _smart_fallback(msg)
            return jsonify({"ok": True, "data": result})

    if skill_mod:
        text, chart = _run_skill(skill_id, msg)
        resp = {"ok": True, "data": text, "skill": skill_id}
        if chart:
            resp["chart_data"] = chart
        return jsonify(resp)

    result = _smart_fallback(msg)
    return jsonify({"ok": True, "data": result})


@app.route("/api/conversations", methods=["GET"])
def api_list_convs():
    convs = []
    for cid in reversed(conversation_order):
        c = conversations.get(cid)
        if c:
            convs.append({"id": cid, "title": c.get("title", "新对话"), "updated": c.get("updated", "")})
    return jsonify({"ok": True, "data": convs})


@app.route("/api/conversations", methods=["POST"])
def api_create_conv():
    cid = str(uuid.uuid4())[:8]
    now = datetime.now().isoformat()
    conversations[cid] = {
        "id": cid,
        "title": "新对话",
        "messages": [],
        "created": now,
        "updated": now,
    }
    conversation_order.append(cid)
    return jsonify({"ok": True, "data": {"id": cid}})


@app.route("/api/conversations/<cid>", methods=["GET"])
def api_get_conv(cid):
    c = conversations.get(cid)
    if not c:
        return jsonify({"ok": False, "error": "Not found"}), 404
    return jsonify({"ok": True, "data": c})


@app.route("/api/conversations/<cid>", methods=["DELETE"])
def api_delete_conv(cid):
    if cid in conversations:
        del conversations[cid]
        if cid in conversation_order:
            conversation_order.remove(cid)
    return jsonify({"ok": True})


# ===== Task API =====

@app.route("/api/tasks", methods=["GET"])
def api_list_tasks():
    tm = getattr(app, '_task_manager', None)
    if tm is None:
        return jsonify({"ok": True, "data": []})
    return jsonify({"ok": True, "data": tm.list_tasks()})


@app.route("/api/tasks/conditions", methods=["GET"])
def api_list_conditions():
    return jsonify({"ok": True, "data": CONDITION_DESC})


@app.route("/api/tasks", methods=["POST"])
def api_create_task():
    tm = getattr(app, '_task_manager', None)
    if tm is None:
        return jsonify({"ok": False, "error": "TaskManager not started"}), 503
    body = request.get_json(force=True)
    ttype = body.get("type", "scheduled")
    name = body.get("name", "").strip()
    prompt = body.get("prompt", "").strip()
    if not name or not prompt:
        return jsonify({"ok": False, "error": "name and prompt required"})

    if ttype == "scheduled":
        interval = int(body.get("interval", 3600))
        task = ScheduledTask(name, prompt, interval)
    else:
        condition_id = body.get("condition_id", "")
        cooldown = int(body.get("cooldown", 86400))
        task = TriggerTask(name, prompt, condition_id, cooldown)

    tm.add(task)
    return jsonify({"ok": True, "data": task.to_dict()})


@app.route("/api/tasks/<task_id>", methods=["DELETE"])
def api_delete_task(task_id):
    tm = getattr(app, '_task_manager', None)
    if tm is None:
        return jsonify({"ok": False, "error": "TaskManager not started"}), 503
    ok = tm.remove(task_id)
    return jsonify({"ok": ok})


@app.route("/api/tasks/log", methods=["GET"])
def api_task_log():
    tm = getattr(app, '_task_manager', None)
    if tm is None:
        return jsonify({"ok": True, "data": []})
    limit = request.args.get("limit", 20, type=int)
    return jsonify({"ok": True, "data": tm.get_log(limit)})


# ===== Permission API =====

@app.route("/api/permissions", methods=["GET"])
def api_list_permissions():
    pm = getattr(app, '_permission_manager', None) or PermissionManager.get_instance()
    return jsonify({"ok": True, "data": pm.list_rules()})


@app.route("/api/permissions", methods=["POST"])
def api_set_permission():
    pm = getattr(app, '_permission_manager', None) or PermissionManager.get_instance()
    body = request.get_json(force=True)
    action_id = body.get("action_id", "")
    level = body.get("level")
    if not action_id or level is None:
        return jsonify({"ok": False, "error": "action_id and level required"})
    if isinstance(level, str):
        level = PermissionLevel.from_name(level)
    pm.set_rule(action_id, int(level))
    return jsonify({"ok": True, "data": pm.get_rule(action_id)})


@app.route("/api/permissions/approve", methods=["POST"])
def api_approve_permission():
    pm = getattr(app, '_permission_manager', None) or PermissionManager.get_instance()
    body = request.get_json(force=True)
    pending_id = body.get("pending_id", "")
    skill_id = body.get("skill_id", "")
    msg = body.get("message", "")

    result = pm.approve(pending_id)
    if result["status"] != "approved":
        return jsonify({"ok": False, "error": "Invalid or expired pending_id"})

    if skill_id and get_skill(skill_id):
        text, chart = _run_skill(skill_id, msg)
        resp = {"ok": True, "data": text, "skill": skill_id}
        if chart:
            resp["chart_data"] = chart
        return jsonify(resp)

    return jsonify({"ok": True, "data": "操作已批准。请重新发送消息。"})


@app.route("/api/permissions/deny", methods=["POST"])
def api_deny_permission():
    pm = getattr(app, '_permission_manager', None) or PermissionManager.get_instance()
    body = request.get_json(force=True)
    pending_id = body.get("pending_id", "")
    result = pm.deny(pending_id)
    return jsonify({"ok": True, "data": "操作已被拒绝。"})


def _setup_permissions():
    pm = PermissionManager.get_instance()
    app._permission_manager = pm
    return pm


def _setup_task_manager():
    tm = TaskManager.get_instance()
    tm.set_agent_factory(lambda: _agent)
    tm.start()  # Load persisted tasks first

    existing = tm.list_tasks()
    if not existing:
        tm.add(TriggerTask(
            name="学分不足预警",
            prompt="检测到学生 {student} 存在学分缺口风险：{reason}。请生成详细的学业预警报告，包括学分统计、差距分析、补救建议和推荐课程。",
            condition_id="credit_shortage",
            cooldown=86400,
        ))
        tm.add(TriggerTask(
            name="GPA 过低预警",
            prompt="学生 {student} 当前 GPA 为 {gpa}，请生成 GPA 预警报告，分析原因并提供提升建议。",
            condition_id="low_gpa",
            cooldown=86400,
        ))
        tm.add(ScheduledTask(
            name="每日学习建议",
            prompt="请根据当前日期生成一份每日学习建议，包括：1) 推荐今日复习的课程 2) 学习技巧分享 3) 激励语录。",
            interval=86400,
        ))

    app._task_manager = tm


def run_web(host="0.0.0.0", port=8000, debug=False):
    from ..utils.logger import get_logger
    logger = get_logger("web", logging.INFO)
    logger.info(f"EduClaw Web UI starting at http://{host}:{port}")
    _init_llm()
    if _llm_available:
        logger.info(f"LLM ready: {_agent_model}")
    else:
        logger.info("LLM not available — running in tool-only mode")
    _setup_task_manager()
    _setup_permissions()
    tm = getattr(app, '_task_manager', None)
    pm = getattr(app, '_permission_manager', None)
    logger.info(f"TaskManager: {len(tm.list_tasks()) if tm else 0} tasks, "
                f"Permissions: {len(pm.list_rules()) if pm else 0} rules")
    app.run(host=host, port=port, debug=debug)
