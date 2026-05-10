from agentscope.tool import Toolkit, ToolResponse
from agentscope.message import TextBlock

from ....models.profile import StudentProfile, AbilityScore, GradeRecord, AbilityType
from ....core.data_loader import get_student
from ....core.auth import get_current_student

ABILITY_COURSE_MAPPING = {
    AbilityType.PROGRAMMING: {"keywords": ["编程", "程序设计", "Python", "Java", "C++"], "courses": ["程序设计基础", "面向对象程序设计", "数据结构", "软件开发实践"]},
    AbilityType.ALGORITHM: {"keywords": ["算法", "数据结构", "离散数学"], "courses": ["数据结构与算法", "离散数学", "算法设计与分析"]},
    AbilityType.SYSTEM_DESIGN: {"keywords": ["系统", "架构", "设计", "分布式"], "courses": ["操作系统", "计算机网络", "分布式系统", "软件工程"]},
    AbilityType.DATABASE: {"keywords": ["数据库", "SQL", "数据", "存储"], "courses": ["数据库原理", "数据库应用", "大数据技术"]},
    AbilityType.PROJECT_MANAGEMENT: {"keywords": ["管理", "项目", "团队", "敏捷"], "courses": ["软件项目管理", "敏捷开发", "系统工程"]},
    AbilityType.COMMUNICATION: {"keywords": ["沟通", "表达", "演讲", "写作"], "courses": ["沟通技巧", "技术写作", "演讲与表达"]},
    AbilityType.LEARNING_ABILITY: {"keywords": ["学习", "自主", "研究", "方法"], "courses": ["学习方法论", "研究方法"]},
    AbilityType.INNOVATION: {"keywords": ["创新", "创造", "设计思维", "创业"], "courses": ["创新思维", "设计思维", "创新创业"]},
}
ABILITY_NAMES = {
    AbilityType.PROGRAMMING: "编程开发", AbilityType.ALGORITHM: "算法设计",
    AbilityType.SYSTEM_DESIGN: "系统设计", AbilityType.DATABASE: "数据库应用",
    AbilityType.PROJECT_MANAGEMENT: "项目管理", AbilityType.COMMUNICATION: "沟通协作",
    AbilityType.LEARNING_ABILITY: "学习能力", AbilityType.INNOVATION: "创新能力",
}


def _is_relevant(course_name, keywords, courses):
    for kw in keywords:
        if kw in course_name:
            return True
    for c in courses:
        if c in course_name:
            return True
    return False


def _compute_score(courses, ability_type):
    total_credit = sum(c.credit for c in courses)
    if total_credit == 0:
        return AbilityScore(ability_type=ability_type, score=60.0, level="C")
    weighted = sum(c.score * c.credit for c in courses) / total_credit
    level = "S" if weighted >= 90 else "A" if weighted >= 85 else "B" if weighted >= 75 else "C" if weighted >= 60 else "D"
    evidence = [f"{c.course_name}: {c.score}分" for c in courses[:5]]
    return AbilityScore(ability_type=ability_type, score=round(weighted, 1), level=level, evidence=evidence)


async def generate_profile(student_id: str, name: str, major: str, grade: str) -> ToolResponse:
    """生成学生能力画像。基于学生成绩数据计算8项能力指标得分并给出学习建议。"""
    student = get_current_student()
    sid = student.get("student_id", student_id or "demo_user")
    grades_data = student.get("grade_records", [])
    grade_records = [GradeRecord(**g) for g in grades_data]
    profile = StudentProfile(student_id=sid,
                             name=student.get("name", name or "Demo"),
                             major=student.get("major", major or "计算机科学与技术"),
                             grade=student.get("grade", grade or "大二"),
                             grade_records=grade_records)

    for at, mapping in ABILITY_COURSE_MAPPING.items():
        relevant = [r for r in profile.grade_records if _is_relevant(r.course_name, mapping["keywords"], mapping["courses"])]
        profile.ability_scores[at] = _compute_score(relevant, at) if relevant else AbilityScore(ability_type=at, score=60.0, level="C", evidence=["暂无相关课程数据"])

    gpa = profile.calculate_gpa()
    sorted_ab = sorted(profile.ability_scores.items(), key=lambda x: x[1].score, reverse=True)
    best, worst = sorted_ab[0], sorted_ab[-1]
    summary = f"{name}（{major} {grade}），整体GPA：{gpa:.2f}，擅长能力：{ABILITY_NAMES[best[0]]}（{best[1].level}级），待提升：{ABILITY_NAMES[worst[0]]}（{worst[1].level}级）。"
    profile.summary = summary

    recs = [f"建议加强{ABILITY_NAMES[at]}能力，可选修{ABILITY_COURSE_MAPPING[at]['courses'][0]}等课程" for at, so in profile.ability_scores.items() if so.level in ("C", "D")]
    if gpa < 2.0: recs.append("整体成绩较低，建议调整学习方法")
    elif gpa >= 3.5: recs.append("成绩优异，可考虑参与科研项目或竞赛进一步提升")
    profile.recommendations = recs

    lines = ["学生能力画像", "=" * 40, profile.summary, "", "能力得分", "-" * 40]
    for at, so in profile.ability_scores.items():
        lines.append(f"  {ABILITY_NAMES[at]}: {so.score:5.1f}分 ({so.level}级)")
    lines.extend(["", "学习建议", "-" * 40])
    for i, rec in enumerate(recs, 1):
        lines.append(f"  {i}. {rec}")
    lines.extend(["", f"GPA: {gpa:.2f} | 已修课程: {len(grade_records)}门"])

    return ToolResponse(content=[TextBlock(type="text", text="\n".join(lines))])


def run(prompt: str = ""):
    import asyncio
    student = get_current_student()
    result = asyncio.run(generate_profile(
        student.get("student_id", "demo_user"),
        student.get("name", "Demo"),
        student.get("major", "计算机科学与技术"),
        student.get("grade", "大二")))
    text = ""
    if hasattr(result, "content") and result.content:
        block = result.content[0]
        text = block.text if hasattr(block, "text") else block.get("text", str(block))
    if not text:
        text = str(result)

    score_map = {}
    for line in text.split("\n"):
        for name_cn in ABILITY_NAMES.values():
            if name_cn in line and "分" in line:
                try:
                    ps = line.strip().split(": ")
                    if len(ps) >= 2:
                        score_map[name_cn] = float(ps[1].strip().split("分")[0].strip())
                except (ValueError, IndexError):
                    pass

    labels, values, point_colors = [], [], []
    level_colors = {"S": "#059669", "A": "#2563eb", "B": "#7c3aed", "C": "#d97706", "D": "#dc2626"}
    for at in [AbilityType.PROGRAMMING, AbilityType.ALGORITHM, AbilityType.SYSTEM_DESIGN,
               AbilityType.DATABASE, AbilityType.PROJECT_MANAGEMENT, AbilityType.COMMUNICATION,
               AbilityType.LEARNING_ABILITY, AbilityType.INNOVATION]:
        name = ABILITY_NAMES[at]
        s = score_map.get(name, 60.0)
        labels.append(name)
        values.append(round(s, 1))
        lvl = "S" if s >= 90 else "A" if s >= 85 else "B" if s >= 75 else "C" if s >= 60 else "D"
        point_colors.append(level_colors[lvl])

    return {"text": text, "chart_data": {"labels": labels, "values": values, "pointColors": point_colors, "maxScore": 100}}


toolkit = Toolkit()
toolkit.register_tool_function(generate_profile)
