import uuid
from agentscope.tool import Toolkit, ToolResponse
from agentscope.message import TextBlock

from ....models.warning import WarningAlert, WarningRule, WarningLevel, WarningType
from ....core.data_loader import load_warning_rules
from ....core.auth import get_current_student


def _build_rules(raw: dict) -> dict:
    """从 JSON 字典构建 WarningRule 对象。"""
    result = {}
    for rid, r in raw.items():
        result[rid] = WarningRule(
            rule_id=r["rule_id"],
            name=r["name"],
            warning_type=WarningType(r.get("warning_type", "low_gpa")),
            level=WarningLevel(r.get("level", "warning")),
            condition=r.get("condition", ""),
            message_template=r.get("message_template", ""),
            action_suggestions=r.get("action_suggestions", []),
            enabled=r.get("enabled", True),
        )
    return result


async def check_student_warning(student_id: str) -> ToolResponse:
    """检查学生的学业预警状态，包括GPA、挂科、学分不足等情况。当用户想了解学业预警信息时使用此工具。"""
    student = get_current_student()
    profile = {
        "student_id": student.get("student_id", student_id),
        "name": student.get("name", "Demo User"),
        "gpa": student.get("gpa", 3.0),
        "total_credits": student.get("total_credits", 0),
        "required_credits": student.get("required_credits", 140),
        "grade_records": student.get("grade_records", []),
    }
    rules_raw = load_warning_rules()
    rules = _build_rules(rules_raw) if rules_raw else {}
    alerts = []
    gpa = profile.get("gpa", 0)

    for rule in rules.values():
        if not rule.enabled:
            continue
        trigger = False
        variables = {}
        if rule.warning_type == WarningType.LOW_GPA:
            variables["gpa"] = gpa
            trigger = (gpa < 2.0) if "2.0" in rule.condition else (gpa < 2.5)
        elif rule.warning_type == WarningType.FAILED_COURSE:
            failed = [g for g in profile.get("grade_records", []) if g.get("score", 0) < 60]
            if failed:
                trigger = True
                variables["count"] = len(failed)
                variables["courses"] = ", ".join(g["course_name"] for g in failed)
        elif rule.warning_type == WarningType.MISSING_CREDIT:
            total_credit = sum(g.get("credit", 0) for g in profile.get("grade_records", []) if g.get("score", 0) >= 60)
            gap = 140 - total_credit
            variables["credit_gap"] = gap
            trigger = gap > 10
        if trigger:
            message = rule.message_template.format(**variables)
            alerts.append(WarningAlert(alert_id=str(uuid.uuid4()), student_id=student_id, rule_id=rule.rule_id, warning_type=rule.warning_type, level=rule.level, message=message, actions=rule.action_suggestions))

    level_order = [WarningLevel.CRITICAL, WarningLevel.DANGER, WarningLevel.WARNING, WarningLevel.INFO]
    level_emoji = {WarningLevel.CRITICAL: "[严重]", WarningLevel.DANGER: "[危险]", WarningLevel.WARNING: "[提醒]", WarningLevel.INFO: "[提示]"}
    alerts.sort(key=lambda a: level_order.index(a.level))

    if not alerts:
        text = f"学生 {profile['name']} 当前学业状况良好，无预警信息。GPA: {gpa:.2f}"
    else:
        lines = ["学业预警报告", f"学生：{profile['name']}", f"GPA：{gpa:.2f}", f"已修课程：{len(profile.get('grade_records', []))}门", "=" * 50]
        for i, alert in enumerate(alerts, 1):
            emoji = level_emoji.get(alert.level, "")
            lines.append(f"\n{emoji} 预警 {i}")
            lines.append(f"   {alert.message}")
            lines.extend(["   建议措施："] + [f"   - {a}" for a in alert.actions])
        lines.append("\n如需进一步帮助，请联系辅导员或学业导师。")
        text = "\n".join(lines)
    return ToolResponse(content=[TextBlock(type="text", text=text)])


def run(prompt: str = "") -> str:
    import asyncio
    result = asyncio.run(check_student_warning("demo_user"))
    if hasattr(result, "content") and result.content:
        block = result.content[0]
        return block.text if hasattr(block, "text") else block.get("text", str(block))
    return str(result)


toolkit = Toolkit()
toolkit.register_tool_function(check_student_warning)
