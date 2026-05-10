from typing import Dict, List, Any

from agentscope.tool import Toolkit, ToolResponse
from agentscope.message import TextBlock

from ..models.profile import StudentProfile, AbilityScore, GradeRecord, AbilityType

ABILITY_COURSE_MAPPING = {
    AbilityType.PROGRAMMING: {
        "keywords": ["编程", "程序设计", "Python", "Java", "C++"],
        "courses": ["程序设计基础", "面向对象程序设计", "数据结构", "软件开发实践"],
    },
    AbilityType.ALGORITHM: {
        "keywords": ["算法", "数据结构", "离散数学"],
        "courses": ["数据结构与算法", "离散数学", "算法设计与分析"],
    },
    AbilityType.SYSTEM_DESIGN: {
        "keywords": ["系统", "架构", "设计", "分布式"],
        "courses": ["操作系统", "计算机网络", "分布式系统", "软件工程"],
    },
    AbilityType.DATABASE: {
        "keywords": ["数据库", "SQL", "数据", "存储"],
        "courses": ["数据库原理", "数据库应用", "大数据技术"],
    },
    AbilityType.PROJECT_MANAGEMENT: {
        "keywords": ["管理", "项目", "团队", "敏捷"],
        "courses": ["软件项目管理", "敏捷开发", "系统工程"],
    },
    AbilityType.COMMUNICATION: {
        "keywords": ["沟通", "表达", "演讲", "写作"],
        "courses": ["沟通技巧", "技术写作", "演讲与表达"],
    },
    AbilityType.LEARNING_ABILITY: {
        "keywords": ["学习", "自主", "研究", "方法"],
        "courses": ["学习方法论", "研究方法"],
    },
    AbilityType.INNOVATION: {
        "keywords": ["创新", "创造", "设计思维", "创业"],
        "courses": ["创新思维", "设计思维", "创新创业"],
    },
}

ABILITY_NAMES = {
    AbilityType.PROGRAMMING: "编程开发",
    AbilityType.ALGORITHM: "算法设计",
    AbilityType.SYSTEM_DESIGN: "系统设计",
    AbilityType.DATABASE: "数据库应用",
    AbilityType.PROJECT_MANAGEMENT: "项目管理",
    AbilityType.COMMUNICATION: "沟通协作",
    AbilityType.LEARNING_ABILITY: "学习能力",
    AbilityType.INNOVATION: "创新能力",
}


def _is_course_relevant(course_name: str, keywords: List[str], courses: List[str]) -> bool:
    for kw in keywords:
        if kw in course_name:
            return True
    for c in courses:
        if c in course_name:
            return True
    return False


def _compute_score(courses: List[GradeRecord], ability_type: AbilityType) -> AbilityScore:
    total_credit = sum(c.credit for c in courses)
    if total_credit == 0:
        return AbilityScore(ability_type=ability_type, score=60.0, level="C")

    weighted = sum(c.score * c.credit for c in courses) / total_credit
    if weighted >= 90:
        level = "S"
    elif weighted >= 85:
        level = "A"
    elif weighted >= 75:
        level = "B"
    elif weighted >= 60:
        level = "C"
    else:
        level = "D"

    evidence = [f"{c.course_name}: {c.score}分" for c in courses[:5]]
    return AbilityScore(ability_type=ability_type, score=round(weighted, 1), level=level, evidence=evidence)


async def generate_profile(
    student_id: str,
    name: str,
    major: str,
    grade: str,
) -> ToolResponse:
    """生成学生能力画像。基于学生成绩数据计算8项能力指标得分并给出学习建议。
    参数: student_id-学生ID, name-姓名, major-专业, grade-年级。当用户想查看能力画像时使用此工具。"""
    # 使用模拟成绩数据
    grades_data = [
        {"course_id": "CS101", "course_name": "程序设计基础", "credit": 3.0, "score": 88, "semester": "2024-1", "category": "专业课", "attributes": ["编程"]},
        {"course_id": "CS102", "course_name": "数据结构与算法", "credit": 4.0, "score": 76, "semester": "2024-1", "category": "专业课", "attributes": ["算法"]},
        {"course_id": "MATH101", "course_name": "高等数学", "credit": 4.0, "score": 82, "semester": "2024-1", "category": "基础课", "attributes": ["数学"]},
        {"course_id": "CS201", "course_name": "面向对象程序设计", "credit": 3.0, "score": 91, "semester": "2024-2", "category": "专业课", "attributes": ["编程"]},
        {"course_id": "CS202", "course_name": "数据库原理", "credit": 3.0, "score": 79, "semester": "2024-2", "category": "专业课", "attributes": ["数据库"]},
        {"course_id": "MATH102", "course_name": "线性代数", "credit": 3.0, "score": 85, "semester": "2024-2", "category": "基础课", "attributes": ["数学"]},
    ]

    grade_records = [
        GradeRecord(
            course_id=g["course_id"], course_name=g["course_name"],
            credit=g["credit"], score=g["score"],
            semester=g["semester"], category=g["category"],
            attributes=g.get("attributes", []),
        )
        for g in grades_data
    ]

    profile = StudentProfile(
        student_id=student_id, name=name, major=major, grade=grade,
        grade_records=grade_records,
    )

    for ability_type, mapping in ABILITY_COURSE_MAPPING.items():
        relevant = [
            r for r in profile.grade_records
            if _is_course_relevant(r.course_name, mapping["keywords"], mapping["courses"])
        ]
        if relevant:
            profile.ability_scores[ability_type] = _compute_score(relevant, ability_type)
        else:
            profile.ability_scores[ability_type] = AbilityScore(
                ability_type=ability_type, score=60.0, level="C",
                evidence=["暂无相关课程数据"],
            )

    # Summary
    gpa = profile.calculate_gpa()
    sorted_abilities = sorted(profile.ability_scores.items(), key=lambda x: x[1].score, reverse=True)
    summary_parts = [f"{name}（{major} {grade}）", f"整体GPA：{gpa:.2f}"]
    if sorted_abilities:
        best = sorted_abilities[0]
        worst = sorted_abilities[-1]
        summary_parts.append(f"擅长能力：{ABILITY_NAMES.get(best[0], best[0].value)}（{best[1].level}级）")
        if best != worst:
            summary_parts.append(f"待提升：{ABILITY_NAMES.get(worst[0], worst[0].value)}（{worst[1].level}级）")
    profile.summary = "，".join(summary_parts) + "。"

    # Recommendations
    recs = []
    for at, score_obj in profile.ability_scores.items():
        if score_obj.level in ("C", "D"):
            recs.append(f"建议加强{ABILITY_NAMES.get(at, at.value)}能力，可选修{ABILITY_COURSE_MAPPING[at]['courses'][0]}等课程")
    if gpa < 2.0:
        recs.append("整体成绩较低，建议调整学习方法，加强基础课程学习")
    elif gpa >= 3.5:
        recs.append("成绩优异，可考虑参与科研项目或竞赛进一步提升")
    profile.recommendations = recs

    # Format response
    lines = ["学生能力画像", "=" * 40, profile.summary, "", "能力得分", "-" * 40]
    for at, score_obj in profile.ability_scores.items():
        name_cn = ABILITY_NAMES.get(at, at.value)
        lines.append(f"  {name_cn}: {score_obj.score:5.1f}分 ({score_obj.level}级)")
    lines.extend(["", "学习建议", "-" * 40])
    for i, rec in enumerate(recs, 1):
        lines.append(f"  {i}. {rec}")
    lines.extend(["", f"GPA: {gpa:.2f} | 已修课程: {len(grade_records)}门"])

    return ToolResponse(content=[TextBlock(type="text", text="\n".join(lines))])


profile_toolkit = Toolkit()
profile_toolkit.register_tool_function(generate_profile)
