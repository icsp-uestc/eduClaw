"""
EduClaw - 教育伴学智能体系统

基于 AgentScope 框架构建的智能教育伴学系统，
提供能力画像生成、课程检索、学业预警等服务。
"""

__version__ = "2.0.0"
__author__ = "EduClaw Team"

from .agents.edu_assistant import create_edu_agent
from .main import run_demo, run_interactive

__all__ = [
    "create_edu_agent",
    "run_demo",
    "run_interactive",
]
