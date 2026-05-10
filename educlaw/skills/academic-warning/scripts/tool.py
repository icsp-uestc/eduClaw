import uuid
from agentscope.tool import Toolkit, ToolResponse
from agentscope.message import TextBlock

from ....models.warning import WarningAlert, WarningRule, WarningLevel, WarningType

DEFAULT_RULES = {
    "gpa_below_2.0": WarningRule(rule_id="gpa_below_2.0", name="GPA低于2.0预警", warning_type=WarningType.LOW_GPA, level=WarningLevel.DANGER, condition="gpa < 2.0", message_template="您的GPA为{gpa:.2f}，已低于2.0预警线。请注意调整学习状态！", action_suggestions=["及时向任课老师请教", "参加学习辅导班", "与辅导员或学业导师沟通"]),
    "gpa_below_2.5": WarningRule(rule_id="gpa_below_2.5", name="GPA低于2.5提醒", warning_type=WarningType.LOW_GPA, level=WarningLevel.WARNING, condition="gpa < 2.5", message_template="您的GPA为{gpa:.2f}，接近预警线。建议加强重点课程学习！", action_suggestions=["重点突破薄弱课程", "制定详细学习计划"]),
    "failed_course": WarningRule(rule_id="failed_course", name="课程不及格预警", warning_type=WarningType.FAILED_COURSE, level=WarningLevel.CRITICAL, condition="has_failed_course", message_template="您有{count}门课程不及格：{courses}。请尽快安排补考或重修！", action_suggestions=["联系教务处了解补考安排", "准备补考复习计划", "必要时申请重修"]),
    "ability_decline": WarningRule(rule_id="ability_decline", name="能力下降预警", warning_type=WarningType.ABILITY_DECLINE, level=WarningLevel.WARNING, condition="ability_score_decline", message_template="您的{ability}能力得分从{old_score}下降到{new_score}，请注意加强相关学习！", action_suggestions=["复习相关课程内容", "选修提升该能力的课程", "参加相关实践活动"]),
    "credit_shortage": WarningRule(rule_id="credit_shortage", name="学分不足预警", warning_type=WarningType.MISSING_CREDIT, level=WarningLevel.WARNING, condition="credit_gap > 10", message_template="距离毕业要求还差{credit_gap}学分，请合理安排后续选课！", action_suggestions=["查询剩余必修课程", "规划后续学期的选课计划", "考虑暑期课程"]),
}


async def check_student_warning(student_id: str) -> ToolResponse:
    """检查学生的学业预警状态，包括GPA、挂科、学分不足等情况。当用户想了解学业预警信息时使用此工具。"""
    profile = {
        "student_id": student_id, "name": "Demo User", "gpa": 3.12,
        "grade_records": [
            {"course_id": "CS101", "course_name": "程序设计基础", "credit": 3.0, "score": 88, "semester": "2024-1"},
            {"course_id": "CS102", "course_name": "数据结构与算法", "credit": 4.0, "score": 76, "semester": "2024-1"},
            {"course_id": "MATH101", "course_name": "高等数学", "credit": 4.0, "score": 82, "semester": "2024-1"},
            {"course_id": "CS201", "course_name": "面向对象程序设计", "credit": 3.0, "score": 91, "semester": "2024-2"},
            {"course_id": "CS202", "course_name": "数据库原理", "credit": 3.0, "score": 79, "semester": "2024-2"},
            {"course_id": "MATH102", "course_name": "线性代数", "credit": 3.0, "score": 85, "semester": "2024-2"},
        ],
    }
    alerts = []
    gpa = profile.get("gpa", 0)

    for rule in DEFAULT_RULES.values():
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
