from typing import Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class WarningLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    DANGER = "danger"
    CRITICAL = "critical"


class WarningType(Enum):
    LOW_GPA = "low_gpa"
    FAILED_COURSE = "failed_course"
    MISSING_CREDIT = "missing_credit"
    ABILITY_DECLINE = "ability_decline"
    COURSE_DEADLINE = "course_deadline"
    REGISTRATION = "registration"


@dataclass
class WarningRule:
    rule_id: str
    name: str
    warning_type: WarningType
    level: WarningLevel
    condition: str
    message_template: str
    action_suggestions: List[str] = field(default_factory=list)
    enabled: bool = True


@dataclass
class WarningAlert:
    alert_id: str
    student_id: str
    rule_id: str
    warning_type: WarningType
    level: WarningLevel
    message: str
    actions: List[str]
    created_at: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False
    resolved: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "student_id": self.student_id,
            "rule_id": self.rule_id,
            "warning_type": self.warning_type.value,
            "level": self.level.value,
            "message": self.message,
            "actions": self.actions,
            "created_at": self.created_at.isoformat(),
            "acknowledged": self.acknowledged,
            "resolved": self.resolved,
        }
