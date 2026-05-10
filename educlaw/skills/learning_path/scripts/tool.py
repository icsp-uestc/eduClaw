from agentscope.tool import Toolkit, ToolResponse
from agentscope.message import TextBlock

from ....core.mock_data import COURSE_DATABASE, PATH_DATABASE
from ....core.nl2sql import NL2SQLParser
from ....models.course import LearningPath

nl2sql = NL2SQLParser()


def _format_path(path: LearningPath) -> str:
    lines = [
        f"学习路径：{path.name}", "=" * 50,
        f"\n目标能力：{', '.join(path.target_abilities)}",
        f"预计时长：{path.estimated_duration} 个学期",
        f"总学分数：{path.total_credits}",
        f"\n描述：{path.description}",
        "\n学期安排：",
    ]
    for i, semester_courses in enumerate(path.semesters, 1):
        lines.append(f"\n第{i}学期：")
        for cid in semester_courses:
            if cid in COURSE_DATABASE:
                c = COURSE_DATABASE[cid]
                lines.append(f"  - {c.course_name} ({c.credit}学分)")
    return "\n".join(lines)


def _match_path(target: str) -> LearningPath:
    """使用 NL2SQL 提取关键词进行模糊匹配，而非直接 in 判断。"""
    keywords, _ = nl2sql.parse(target)
    best_path = None
    best_score = 0
    for path in PATH_DATABASE.values():
        score = 0
        path_text = path.name + " " + path.description + " " + " ".join(path.target_abilities)
        for kw in keywords:
            if kw in path_text:
                score += 1
        # 也检查原始输入中的关键词片段
        if any(frag in path.name for frag in ["后端", "前端", "全栈", "AI", "人工智能"]):
            for frag in ["后端", "前端", "全栈", "AI", "人工智能"]:
                if frag in target:
                    if frag in path.name or frag in path.description:
                        score += 5
        if score > best_score:
            best_score = score
            best_path = path
    return best_path or PATH_DATABASE.get("backend_dev", list(PATH_DATABASE.values())[0])


async def generate_learning_path(target: str) -> ToolResponse:
    """根据目标职业方向生成个性化学习路径，包含学期课程安排。当用户想规划学习路线时使用此工具。"""
    base_path = _match_path(target)
    return ToolResponse(content=[TextBlock(type="text", text=_format_path(base_path))])


def run(prompt: str = "") -> str:
    from ..._async_compat import run_async
    result = run_async(generate_learning_path(prompt or "后端开发工程师"))
    if hasattr(result, "content") and result.content:
        block = result.content[0]
        return block.text if hasattr(block, "text") else block.get("text", str(block))
    return str(result)


toolkit = Toolkit()
toolkit.register_tool_function(generate_learning_path)
