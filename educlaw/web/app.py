import asyncio
import os
import uuid
import logging
from datetime import datetime

from flask import Flask, render_template, request, jsonify, session

from ..service.agent_service import AgentService
from ..skills import list_skills, get_skill
from ..tasks import TaskManager, ScheduledTask, TriggerTask, CONDITION_DESC
from ..permissions import PermissionManager, PermissionLevel
from ..core.auth import ensure_login, login as auth_login, logout as auth_logout, get_current_student, get_current_user_id, get_current_user_name, get_available_users, is_logged_in

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.urandom(24)

# ---- Agent Service ----
_agent_service: AgentService = None

# ---- Bot Adapters ----
_feishu_adapter = None


def get_agent_service() -> AgentService:
    return _agent_service


def _init_llm():
    global _agent_service
    if _agent_service is None:
        _agent_service = AgentService()
    _agent_service.init_llm()


def _init_feishu():
    global _feishu_adapter
    from ..platforms.feishu import FeishuBotAdapter
    try:
        _feishu_adapter = FeishuBotAdapter(_agent_service)
        _feishu_adapter.start()
        logging.getLogger("web").info("Feishu Bot started")
    except Exception as e:
        logging.getLogger("web").warning("Feishu Bot init skipped: %s", e)
        _feishu_adapter = None


# ===== Auth API =====

@app.route("/")
def index():
    ensure_login()
    return render_template("index.html")


@app.before_request
def _auto_login():
    if not request.path.startswith("/api/"):
        ensure_login()


@app.route("/api/auth/status")
def api_auth_status():
    student = get_current_student()
    return jsonify({"ok": True, "data": {
        "student_id": student.get("student_id"),
        "name": student.get("name"),
        "major": student.get("major"),
        "grade": student.get("grade"),
        "is_logged_in": is_logged_in(),
    }})


@app.route("/api/auth/users")
def api_auth_users():
    return jsonify({"ok": True, "data": get_available_users()})


@app.route("/api/auth/login", methods=["POST"])
def api_auth_login():
    body = request.get_json(force=True)
    student_id = body.get("student_id", "").strip()
    if not student_id:
        return jsonify({"ok": False, "error": "Missing student_id"})
    user = auth_login(student_id)
    if user is None:
        return jsonify({"ok": False, "error": f"User not found: {student_id}"})
    return jsonify({"ok": True, "data": user})


@app.route("/api/auth/logout", methods=["POST"])
def api_auth_logout():
    auth_logout()
    ensure_login()
    return jsonify({"ok": True, "data": {"student_id": get_current_user_id()}})


@app.route("/api/skills")
def api_skills():
    all_skills = list_skills()
    user_skills = {s["id"]: s for s in all_skills if s["id"] != "interactive_response"}
    return jsonify({"ok": True, "data": user_skills})


@app.route("/api/status")
def api_status():
    svc = get_agent_service()
    return jsonify({"ok": True, "data": {
        "llm_available": svc.llm_available,
        "model": svc.model_name,
        "url": svc.base_url,
        "available_models": svc.available_models,
        "last_error": svc.last_error,
    }})


@app.route("/api/status/test", methods=["POST"])
def api_test_llm():
    svc = get_agent_service()
    result = svc.test_llm()
    if result.get("ok"):
        return jsonify({"ok": True, "data": {"reply": result["reply"], "model": svc.model_name}, "llm_available": True})
    return jsonify({"ok": False, "error": result.get("error", ""), "llm_available": False})


@app.route("/api/status/reconnect", methods=["POST"])
def api_reconnect_llm():
    global _agent_service
    _agent_service = AgentService()
    _agent_service.init_llm()
    svc = get_agent_service()
    return jsonify({
        "ok": svc.llm_available,
        "llm_available": svc.llm_available,
        "model": svc.model_name,
        "error": svc.last_error,
    })


@app.route("/api/chat", methods=["POST"])
def api_chat():
    svc = get_agent_service()
    body = request.get_json(force=True)
    msg = body.get("message", "").strip()
    skill_id = body.get("skill", "")
    conv_id = body.get("conv_id", "")

    if not msg and not skill_id:
        return jsonify({"ok": False, "error": "Empty message"})

    skill_mod = get_skill(skill_id) if skill_id else None
    pm = getattr(app, '_permission_manager', None) or PermissionManager.get_instance()

    if skill_id:
        perm = pm.check(skill_id, {"message": msg})
        if perm["status"] == "denied":
            return jsonify({"ok": True, "data": "操作已被权限系统拒绝。"})
        if perm["status"] == "ask":
            return jsonify({
                "ok": True, "needs_permission": True,
                "pending_id": perm["pending_id"],
                "action_id": skill_id,
                "action_name": skill_mod.skill_name if skill_mod else skill_id,
                "action_desc": skill_mod.skill_desc if skill_mod else "",
                "data": f"需要确认才能执行「{skill_mod.skill_name if skill_mod else skill_id}」。",
            })

    user_id = get_current_user_id()
    user_name = get_current_user_name()

    resp = svc.chat(
        user_id=user_id,
        message=msg,
        skill_id=skill_id,
        conv_id=conv_id,
        user_name=user_name,
    )

    result = {"ok": True, "data": resp.text, "skill": resp.skill_id, "mode": resp.mode}
    if resp.chart_data:
        result["chart_data"] = resp.chart_data
    return jsonify(result)


@app.route("/api/chat/clear", methods=["POST"])
def api_clear_memory():
    svc = get_agent_service()
    svc.clear_memory()
    return jsonify({"ok": True})


@app.route("/api/conversations", methods=["GET"])
def api_list_convs():
    svc = get_agent_service()
    return jsonify({"ok": True, "data": svc.list_convs()})


@app.route("/api/conversations", methods=["POST"])
def api_create_conv():
    svc = get_agent_service()
    cid = svc.create_conv()
    return jsonify({"ok": True, "data": {"id": cid}})


@app.route("/api/conversations/<cid>", methods=["GET"])
def api_get_conv(cid):
    svc = get_agent_service()
    c = svc.get_conv(cid)
    if not c:
        return jsonify({"ok": False, "error": "Not found"}), 404
    return jsonify({"ok": True, "data": c})


@app.route("/api/conversations/<cid>", methods=["DELETE"])
def api_delete_conv(cid):
    svc = get_agent_service()
    svc.delete_conv(cid)
    return jsonify({"ok": True})


@app.route("/api/tasks", methods=["GET"])
def api_list_tasks():
    tm = getattr(app, '_task_manager', None)
    return jsonify({"ok": True, "data": tm.list_tasks() if tm else []})


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
        task = ScheduledTask(name, prompt, int(body.get("interval", 3600)))
    else:
        task = TriggerTask(name, prompt, body.get("condition_id", ""), int(body.get("cooldown", 86400)))
    tm.add(task)
    return jsonify({"ok": True, "data": task.to_dict()})


@app.route("/api/tasks/<task_id>", methods=["DELETE"])
def api_delete_task(task_id):
    tm = getattr(app, '_task_manager', None)
    if tm is None:
        return jsonify({"ok": False}), 503
    return jsonify({"ok": tm.remove(task_id)})


@app.route("/api/tasks/log", methods=["GET"])
def api_task_log():
    tm = getattr(app, '_task_manager', None)
    return jsonify({"ok": True, "data": tm.get_log(request.args.get("limit", 20, type=int)) if tm else []})


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
    svc = get_agent_service()
    pm = getattr(app, '_permission_manager', None) or PermissionManager.get_instance()
    body = request.get_json(force=True)
    pending_id = body.get("pending_id", "")
    skill_id = body.get("skill_id", "")
    msg = body.get("message", "")
    result = pm.approve(pending_id)
    if result["status"] != "approved":
        return jsonify({"ok": False, "error": "Invalid or expired pending_id"})
    if skill_id and get_skill(skill_id):
        skill_mod = get_skill(skill_id)
        user_id = get_current_user_id()
        user_name = get_current_user_name()
        resp = svc.chat(user_id=user_id, message=msg, skill_id=skill_id, user_name=user_name)
        result_data = {"ok": True, "data": resp.text, "skill": skill_id}
        if resp.chart_data:
            result_data["chart_data"] = resp.chart_data
        return jsonify(result_data)
    return jsonify({"ok": True, "data": "操作已批准。"})


@app.route("/api/permissions/deny", methods=["POST"])
def api_deny_permission():
    pm = getattr(app, '_permission_manager', None) or PermissionManager.get_instance()
    body = request.get_json(force=True)
    pending_id = body.get("pending_id", "")
    pm.deny(pending_id)
    return jsonify({"ok": True, "data": "操作已被拒绝。"})


# ===== Feishu Webhook =====

@app.route("/api/feishu/event", methods=["POST"])
def feishu_event():
    """飞书事件回调接收入口。"""
    if _feishu_adapter is None:
        return jsonify({"code": -2, "msg": "Feishu adapter not initialized"}), 503
    try:
        body = request.get_json(force=True)
        result = _feishu_adapter.handle_event(body)
        return jsonify(result)
    except Exception as e:
        logging.getLogger("web").error("Feishu event error: %s", e)
        return jsonify({"code": -1, "msg": str(e)}), 500


# ===== Startup =====

def _setup_task_manager():
    svc = get_agent_service()
    tm = TaskManager.get_instance()
    tm.set_agent_factory(lambda: svc.agent)
    tm.start()
    existing = tm.list_tasks()
    if not existing:
        tm.add(TriggerTask(name="学分不足预警", prompt="检测到学生 {student} 存在学分缺口风险: {reason}。请生成详细的学业预警报告。", condition_id="credit_shortage", cooldown=86400))
        tm.add(TriggerTask(name="GPA 过低预警", prompt="学生 {student} 当前 GPA 为 {gpa}，请生成 GPA 预警报告。", condition_id="low_gpa", cooldown=86400))
        tm.add(ScheduledTask(name="每日学习建议", prompt="请根据当前日期生成一份每日学习建议，包括推荐复习课程、学习技巧、激励语录。", interval=86400))
    app._task_manager = tm


def _setup_permissions():
    pm = PermissionManager.get_instance()
    app._permission_manager = pm
    return pm


def run_web(host="0.0.0.0", port=8000, debug=False, enable_feishu=False):
    global _agent_service, _feishu_adapter
    from ..utils.logger import get_logger
    logger = get_logger("web", logging.INFO)
    logger.info("EduClaw Web UI starting at http://%s:%s", host, port)

    _agent_service = AgentService()
    _agent_service.init_llm()
    logger.info("LLM: %s (model=%s)",
                "connected" if _agent_service.llm_available else "unavailable",
                _agent_service.model_name)

    _setup_task_manager()
    _setup_permissions()
    tm = getattr(app, '_task_manager', None)
    logger.info("Ready: %d tasks, %d permission rules",
                len(tm.list_tasks()) if tm else 0,
                len(PermissionManager.get_instance().list_rules()))

    if enable_feishu:
        _init_feishu()

    app.run(host=host, port=port, debug=debug)
