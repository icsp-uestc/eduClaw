import logging
import re
from typing import List, Tuple

from ..utils.logger import get_logger


class NL2SQLParser:
    KEYWORD_MAPPING = {
        "必修": "course_type = 'required'",
        "选修": "course_type = 'elective'",
        "简单": "difficulty = 'easy'",
        "困难": "difficulty = 'hard'",
        "容易": "difficulty = 'easy'",
        "难": "difficulty = 'hard'",
        "高难度": "difficulty = 'hard'",
        "计算机": "department = 'computer'",
        "软件": "department = 'software'",
        "数学": "department = 'math'",
        "3学分": "credit = 3",
        "2学分": "credit = 2",
        "4学分": "credit = 4",
    }

    def __init__(self):
        self.logger = get_logger("core.nl2sql", logging.INFO)

    def parse(self, natural_query: str) -> Tuple[List[str], str]:
        query = natural_query.lower()
        intent = self._identify_intent(query)
        keywords = self._extract_keywords(query)
        self.logger.debug(f"Parsed: {query} -> intent: {intent}, keywords: {keywords}")
        return keywords, intent

    def _identify_intent(self, query: str) -> str:
        intent_patterns = {
            "recommend": ["推荐", "建议", "想选", "应该", "怎么选"],
            "search": ["找", "搜索", "查", "有没有", "有哪些"],
            "detail": ["介绍", "详细", "内容", "学什么"],
            "prerequisite": ["先修", "前置", "要求", "前提"],
            "plan": ["规划", "路径", "计划", "安排"],
        }
        for intent, patterns in intent_patterns.items():
            for pattern in patterns:
                if pattern in query:
                    return intent
        return "search"

    def _extract_keywords(self, query: str) -> List[str]:
        keywords = []
        for keyword, condition in self.KEYWORD_MAPPING.items():
            if keyword in query:
                keywords.append(condition)

        chinese_words = re.findall(r'[一-鿿]{2,}', query)
        for phrase in chinese_words:
            for i in range(len(phrase) - 1):
                bigram = phrase[i:i + 2]
                if bigram not in keywords:
                    keywords.append(bigram)

        return keywords
