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

    def calculate_gpa(self) -> float:
        if not self.grade_records:
            return 0.0
        total_credits = 0
        total_weighted_score = 0
        for record in self.grade_records:
            total_credits += record.credit
            total_weighted_score += record.score * record.credit
        return total_weighted_score / total_credits if total_credits > 0 else 0.0

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
