# EduClaw 待修复问题清单

> 生成时间：2026-05-10
> 已修复 12 项问题（P0×2, P1×3, P2×3, P3×3），以下为剩余待处理项。

---

## 1. agentscope 环境依赖未安装（阻塞验证）

**优先级：** P0（环境）

**现状：** 当前 macOS 系统 Python (3.13) 未安装 `agentscope`，且 pip 因 SSL 证书问题无法连接 PyPI。所有 skill 的 `scripts/tool.py` 硬依赖 `from agentscope.tool import Toolkit`，导致 `discover_skills()` 加载 0 个 skill。

**影响：** 代码逻辑已全部修复，但无法在当前环境做运行时验证。

**修复步骤：**

```bash
# 方案 A：使用 conda 环境（推荐，项目原配置）
conda activate educlaw
pip install agentscope>=1.0.0
python start.py --skip-llm

# 方案 B：修复系统 Python 的 SSL
pip3 install --trusted-host pypi.org --trusted-host files.pythonhosted.org agentscope
```

---

## 2. 缺少单元测试

**优先级：** P2

**现状：** `requirements.txt` 已列出 `pytest` 和 `pytest-asyncio`，但项目中无任何 `test_*.py` 文件。skill 逻辑相对独立，非常适合单元测试。

**建议结构：**

```
tests/
  conftest.py                  # 公共 fixtures（mock agentscope、mock 数据）
  test_nl2sql.py               # NL2SQLParser 关键词提取测试
  test_skill_registry.py       # discover_skills / list_skills / register_toolkits
  test_course_search.py        # 课程检索逻辑
  test_course_recommend.py     # 课程推荐逻辑
  test_learning_path.py        # 学习路径匹配
  test_student_profile.py      # 能力画像计算 + GPA 换算
  test_academic_warning.py     # 预警规则触发
  test_auth.py                 # auth 模块（Flask 模式 + CLI 模式）
  test_gpa_conversion.py       # 百分制 → 4.0 制转换边界值
```

**关键测试用例：**

- `NL2SQLParser.parse("编程相关的课程")` 应返回 `["编程"]` 而非 `["编程", "程相", "相关", ...]`
- `StudentProfile._score_to_gp(90)` == 4.0, `_score_to_gp(59)` == 0.0
- `_match_path("我想成为后端工程师")` 应匹配到 `backend_dev` 路径
- `_check_condition(course, "department = 'computer'")` 对计算机院系课程返回 True
- `set_current_user("stu001")` 后 `get_current_user_id()` 返回 `"stu001"`

---

## 3. 缺少 Lint / Formatter / 类型检查配置

**优先级：** P3

**现状：** 项目无 `pyproject.toml`、`setup.cfg`、`ruff.toml` 等配置文件，代码风格无统一约束。

**建议：**

```toml
# pyproject.toml
[tool.ruff]
line-length = 120
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP"]

[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
```

---

## 4. 缺少 CI/CD 工作流

**优先级：** P3

**现状：** 无 GitHub Actions / GitLab CI 配置。

**建议添加 `.github/workflows/ci.yml`：**

```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.10"
      - run: pip install -r requirements.txt
      - run: pytest tests/ -v
```

---

## 5. NL2SQLParser 可进一步引入 jieba 分词

**优先级：** P3

**现状：** 当前已用停用词 + 领域关键词优化了分词质量，但仍基于正则切分。对于复杂自然语言查询（如"有没有适合零基础学生的Python入门课"），效果有限。

**升级方案：**

```python
# requirements.txt 添加
jieba>=0.42.1

# nl2sql.py 中替换正则切分
import jieba
words = jieba.lcut(query)
keywords.extend([w for w in words if len(w) >= 2 and w not in _STOP_WORDS])
```

---

## 6. `start.py` 中引用的模块路径需同步检查

**优先级：** P2

**现状：** `educlaw/__init__.py` 已改为懒加载，但 `start.py` 作为入口文件可能直接 `from educlaw import create_edu_agent`。需确认 `start.py` 在新的懒加载模式下仍能正常工作。

**验证命令：**

```bash
conda activate educlaw
python start.py --skip-llm
python start.py --demo
python start.py --web
```

---

## 7. Web UI 模板中可能引用旧的 skill 目录名

**优先级：** P2

**现状：** `educlaw/web/app.py` 或前端模板中，如果有硬编码的 skill 路径引用（如 `skills/course-search`），需要同步改为下划线命名。

**排查命令：**

```bash
grep -r "course-search\|course-recommend\|learning-path\|student-profile\|academic-warning\|interactive-response" \
  --include="*.py" --include="*.html" --include="*.js" \
  /Users/bytedance/eduClaw/educlaw/web/
```

---

## 8. `data/students.json` 中成绩数据与 GPA 阈值的一致性

**优先级：** P2

**现状：** `models/profile.py` 已改用 4.0 制 GPA 计算，但 `data/students.json` 中预设的 `gpa` 字段值（如 `3.12`）可能是旧的百分制加权平均值，而非 4.0 制绩点。需核实 JSON 数据并按需更新。

**排查：**

```bash
cat /Users/bytedance/eduClaw/data/students.json | python3 -m json.tool | grep gpa
```

如果现有值 > 4.0，说明是百分制，需要换算或删除该预设字段（改为运行时计算）。
