from typing import Dict, List, Any
from dataclasses import dataclass, field
from enum import Enum


class CourseType(Enum):
    REQUIRED = "required"
    ELECTIVE = "elective"
    GENERAL = "general"
    PRACTICAL = "practical"


class Difficulty(Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


@dataclass
class Course:
    course_id: str
    course_name: str
    credit: float
    hours: int
    course_type: CourseType
    department: str
    prerequisites: List[str] = field(default_factory=list)
    difficulty: Difficulty = Difficulty.MEDIUM
    attributes: List[str] = field(default_factory=list)
    description: str = ""
    teachers: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "course_id": self.course_id,
            "course_name": self.course_name,
            "credit": self.credit,
            "hours": self.hours,
            "course_type": self.course_type.value,
            "department": self.department,
            "prerequisites": self.prerequisites,
            "difficulty": self.difficulty.value,
            "attributes": self.attributes,
            "description": self.description,
            "teachers": self.teachers,
        }


@dataclass
class LearningPath:
    path_id: str
    name: str
    target_abilities: List[str]
    semesters: List[List[str]]
    total_credits: float
    estimated_duration: int
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path_id": self.path_id,
            "name": self.name,
            "target_abilities": self.target_abilities,
            "semesters": self.semesters,
            "total_credits": self.total_credits,
            "estimated_duration": self.estimated_duration,
            "description": self.description,
        }
