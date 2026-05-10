"""
EduClaw Skills Registry — 基于 Claude Code Skills 规范自动发现并管理技能。

技能规范 (遵循 anthropics/skills 标准):
  skills/<skill-name>/
    SKILL.md              # YAML frontmatter (name, description) + Markdown 指令
    __init__.py            # 导出: skill_id, toolkit, run(prompt)
    scripts/               # 实现脚本 (可选)
      tool.py

新增技能只需:
  1. 在 educlaw/skills/ 下创建目录 (如 skills/my-skill/)
  2. 创建 SKILL.md (含 YAML frontmatter)
  3. 创建 __init__.py 导出 skill_id, toolkit, run()
"""

import importlib
import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger("skills")

_skills: Dict[str, Any] = {}
_loaded = False


def _parse_skill_md(content: str) -> Optional[Dict[str, str]]:
    """解析 SKILL.md 的 YAML frontmatter，提取 name 和 description。"""
    # 匹配 --- ... --- 之间的 YAML
    match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not match:
        return None
    yaml_block = match.group(1)
    metadata = {}
    for line in yaml_block.strip().split('\n'):
        if ':' in line:
            key, _, val = line.partition(':')
            metadata[key.strip()] = val.strip()
    return metadata if 'name' in metadata else None


def discover_skills() -> Dict[str, Any]:
    """自动扫描 educlaw/skills/ 下所有子目录并加载技能。"""
    global _skills, _loaded
    if _loaded:
        return _skills

    package_dir = Path(__file__).parent
    for entry in sorted(package_dir.iterdir()):
        if not entry.is_dir() or entry.name.startswith("_") or entry.name.startswith("."):
            continue
        init_file = entry / "__init__.py"
        if not init_file.exists():
            continue
        try:
            mod = importlib.import_module(f"educlaw.skills.{entry.name}")
            if hasattr(mod, "skill_id"):
                _skills[mod.skill_id] = mod
                logger.debug(f"Loaded skill: {mod.skill_id}")
        except Exception as e:
            logger.warning(f"Failed to load skill '{entry.name}': {e}")

    _loaded = True
    logger.info(f"Discovered {len(_skills)} skills: {list(_skills.keys())}")
    return _skills


def list_skills() -> List[Dict[str, str]]:
    """返回所有技能的摘要列表 (用于 Web UI / API)。"""
    discover_skills()
    return [
        {
            "id": m.skill_id,
            "name": m.skill_name,
            "icon": m.skill_icon,
            "desc": m.skill_desc,
        }
        for m in _skills.values()
    ]


def get_skill(skill_id: str) -> Optional[Any]:
    """按 ID 获取技能模块。"""
    discover_skills()
    return _skills.get(skill_id)


def run_skill(skill_id: str, prompt: str = ""):
    """直接执行一个技能并返回结果。"""
    mod = get_skill(skill_id)
    if mod is None:
        return None
    result = mod.run(prompt or "")
    if isinstance(result, dict):
        return result
    return result


def register_toolkits(target_toolkit):
    """将所有已发现技能的 toolkit 注册到目标 AgentScope Toolkit 中。
    跳过标记为 prompt-only 的技能。"""
    discover_skills()
    for mod in _skills.values():
        if getattr(mod, "is_prompt_only", False):
            continue
        for name, registered in mod.toolkit.tools.items():
            target_toolkit.register_tool_function(registered.original_func)


def get_skill_doc(skill_id: str) -> Optional[str]:
    """读取技能的 SKILL.md 文档。"""
    mod = get_skill(skill_id)
    if mod is None:
        return None
    doc_path = Path(mod.__file__).parent / "SKILL.md"
    if doc_path.exists():
        return doc_path.read_text(encoding="utf-8")
    return None
