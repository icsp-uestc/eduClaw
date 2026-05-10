import logging
import re
from typing import List, Tuple

from ..utils.logger import get_logger

# 常见停用词，过滤无意义的 bigram
_STOP_WORDS = frozenset([
    "什么", "哪些", "怎么", "可以", "能不", "不能", "有没", "没有",
    "想要", "需要", "帮我", "请问", "告诉", "一下", "关于",
    "相关", "方面", "比较", "适合", "推荐", "建议", "所有",
    "如何", "为什么", "是否", "或者", "以及", "还有", "其他",
    "的课", "课程", "学习", "了解", "查看", "搜索", "查找",
])


class NL2SQLParser:
    KEYWORD_MAPPING = {
        "必修": "course_type = 'required'",
        "选修": "course_type = 'elective'",
        "通识": "course_type = 'general'",
        "简单": "difficulty = 'easy'",
        "困难": "difficulty = 'hard'",
        "容易": "difficulty = 'easy'",
        "难": "difficulty = 'hard'",
        "高难度": "difficulty = 'hard'",
        "中等": "difficulty = 'medium'",
        "计算机": "department = 'computer'",
        "软件": "department = 'software'",
        "数学": "department = 'math'",
        "3学分": "credit = 3",
        "2学分": "credit = 2",
        "4学分": "credit = 4",
    }

    # 有意义的领域关键词（优先匹配）
    DOMAIN_KEYWORDS = frozenset([
        "编程", "程序", "算法", "数据", "网络", "操作系统", "数据库",
        "人工智能", "机器学习", "深度学习", "前端", "后端", "全栈",
        "Python", "Java", "C++", "Web", "SQL", "Linux",
        "软件工程", "设计模式", "分布式", "云计算", "大数据",
        "系统", "架构", "安全", "测试", "运维", "DevOps",
    ])

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

        # 1. 匹配预定义的条件映射
        for keyword, condition in self.KEYWORD_MAPPING.items():
            if keyword in query:
                keywords.append(condition)

        # 2. 匹配领域关键词（精确匹配）
        for domain_kw in self.DOMAIN_KEYWORDS:
            if domain_kw.lower() in query:
                keywords.append(domain_kw)

        # 3. 提取英文单词（如 Python, Java）
        english_words = re.findall(r'[a-zA-Z+#]{2,}', query)
        for word in english_words:
            if word.lower() not in [k.lower() for k in keywords]:
                keywords.append(word)

        # 4. 智能中文切分：提取 2-4 字有意义词组，过滤停用词
        chinese_words = re.findall(r'[\u4e00-\u9fff]{2,4}', query)
        for phrase in chinese_words:
            if phrase not in _STOP_WORDS and phrase not in keywords:
                # 检查是否已被条件映射或领域关键词覆盖
                already_covered = any(phrase in kw for kw in keywords)
                if not already_covered:
                    keywords.append(phrase)

        return keywords
