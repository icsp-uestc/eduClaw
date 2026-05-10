from typing import Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class AbilityType(Enum):
    PROGRAMMING = "programming"
    ALGORITHM = "algorithm"
    SYSTEM_DESIGN = "system_design"
    DATABASE = "database"
    PROJECT_MANAGEMENT = "project_management"
    COMMUNICATION = "communication"
    LEARNING_ABILITY = "learning_ability"
    INNOVATION = "innovation"


@dataclass
class AbilityScore:
    ability_type: AbilityType
    score: float
    level: str
    evidence: List[str] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ability_type": self.ability_type.value,
            "score": self.score,
            "level": self.level,
            "evidence": self.evidence,
            "last_updated": self.last_updated.isoformat(),
        }


@dataclass
class GradeRecord:
    course_id: str
    course_name: str
    credit: float
    score: float
    semester: str
    category: str
    attributes: List[str] = field(default_factory=list)


@dataclass
class StudentProfile:
    student_id: str
    name: str
    major: str
    grade: str
    ability_scores: Dict[AbilityType, AbilityScore] = field(default_factory=dict)
    grade_records: List[GradeRecord] = field(default_factory=list)
    summary: str = ""
    recommendations: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    @staticmethod
    def _score_to_gp(score: float) -> float:
        """百分制成绩转换为 4.0 制绩点。"""
        if score >= 90:
            return 4.0
        elif score >= 85:
            return 3.7
        elif score >= 82:
            return 3.3
        elif score >= 78:
            return 3.0
        elif score >= 75:
            return 2.7
        elif score >= 72:
            return 2.3
        elif score >= 68:
            return 2.0
        elif score >= 64:
            return 1.5
        elif score >= 60:
            return 1.0
        else:
            return 0.0

    def calculate_gpa(self) -> float:
        """计算标准 4.0 制 GPA（加权绩点）。"""
        if not self.grade_records:
            return 0.0
        total_credits = 0
        total_weighted_gp = 0
        for record in self.grade_records:
            total_credits += record.credit
            total_weighted_gp += self._score_to_gp(record.score) * record.credit
        return round(total_weighted_gp / total_credits, 2) if total_credits > 0 else 0.0

    def calculate_weighted_avg(self) -> float:
        """计算加权平均分（百分制）。"""
        if not self.grade_records:
            return 0.0
        total_credits = sum(r.credit for r in self.grade_records)
        total_weighted = sum(r.score * r.credit for r in self.grade_records)
        return round(total_weighted / total_credits, 2) if total_credits > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "student_id": self.student_id,
            "name": self.name,
            "major": self.major,
            "grade": self.grade,
            "gpa": self.calculate_gpa(),
            "ability_scores": {
                k.value: v.to_dict() for k, v in self.ability_scores.items()
            },
            "grade_records": [
                {
                    "course_id": r.course_id,
                    "course_name": r.course_name,
                    "credit": r.credit,
                    "score": r.score,
                    "semester": r.semester,
                    "category": r.category,
                    "attributes": r.attributes,
                }
                for r in self.grade_records
            ],
            "summary": self.summary,
            "recommendations": self.recommendations,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
