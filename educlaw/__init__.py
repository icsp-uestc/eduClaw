"""
EduClaw - 教育伴学智能体系统

基于 AgentScope 框架构建的智能教育伴学系统，
提供能力画像生成、课程检索、学业预警等服务。
"""

__version__ = "2.0.0"
__author__ = "EduClaw Team"


def create_edu_agent(*args, **kwargs):
    """懒加载 agent 创建函数，避免顶层强依赖 agentscope。"""
    from .agents.edu_assistant import create_edu_agent as _create
    return _create(*args, **kwargs)


def run_demo(*args, **kwargs):
    """懒加载 demo 运行函数。"""
    from .main import run_demo as _run_demo
    return _run_demo(*args, **kwargs)


def run_interactive(*args, **kwargs):
    """懒加载交互式运行函数。"""
    from .main import run_interactive as _run_interactive
    return _run_interactive(*args, **kwargs)


__all__ = [
    "create_edu_agent",
    "run_demo",
    "run_interactive",
]
