# EduClaw

基于 AgentScope 框架构建的教育伴学智能体系统。

EduClaw 是一个具备全天候后台常驻运行、支持跨通讯软件原生接入以及拥有持久化本地记忆体系的底层智能体运行与编排框架，专注于教育场景，为学生提供能力画像、课程推荐、学业预警等服务。

## 功能特性

### 核心功能

- **能力画像生成**: 解析学生成绩数据，计算多维能力指标得分，生成量化的能力画像
- **课程智能检索**: 使用 RAG 技术和 NL2SQL 实现精准的课程查询
- **学习路径规划**: 基于学生能力和目标，生成个性化的学习路径
- **主动学业预警**: 定时监控学业状况，及时预警挂科、GPA下降等风险
- **考试提醒**: 为即将到来的考试提供提醒和复习建议

### 技术特性

- **模块化设计**: 智能体能力通过 Skills 方式构建，易于扩展
- **多渠道支持**: 支持 Telegram、飞书、微信等多种通讯渠道接入
- **持久化记忆**: 本地记忆系统保证对话和数据的持久化
- **定时任务**: 内置任务调度器，支持主动推送和服务
- **大模型支持**: 支持云端 API 和本地 vLLM 部署

## 项目结构

```
educlaw/
├── core/               # 核心模块
│   ├── agent.py        # 智能体基类
│   └── gateway.py      # 网关服务
├── skills/             # 技能模块
│   ├── profile_generation.py   # 能力画像生成
│   ├── course_retrieval.py     # 课程检索
│   └── academic_warning.py     # 学业预警
├── agents/             # 智能体实现
│   └── edu_assistant.py        # 教育助手
├── memory/             # 记忆存储
│   └── memory_store.py         # 记忆管理
├── config/             # 配置模块
│   └── config.py       # 配置管理
├── utils/              # 工具模块
│   └── logger.py       # 日志工具
├── database/           # 数据库模块（预留）
├── web/                # Web 界面（预留）
└── main.py             # 主程序
```

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置

创建 `.env` 文件或使用配置文件：

```bash
cp .env.example .env
# 编辑 .env 文件，填入必要的配置
```

### 运行

```bash
# 演示模式
python start.py

# 交互模式
python start.py --interactive

# 调试模式
python start.py --debug
```

## 使用示例

### 能力画像生成

```python
from educlaw import EduClaw
from educlaw.skills import ProfileGenerationSkill

skill = ProfileGenerationSkill()
result = skill.generate_profile(
    student_id="ST001",
    name="张三",
    major="计算机科学与技术",
    grade="大二",
    grades_data=[
        {
            "course_id": "CS101",
            "course_name": "程序设计基础",
            "credit": 3.0,
            "score": 85,
            "semester": "2023-秋",
            "category": "必修"
        },
        # ... 更多课程数据
    ]
)
print(result.content)
```

### 课程检索

```python
from educlaw.skills import CourseRetrievalSkill

skill = CourseRetrievalSkill()
result = skill.search_courses("编程相关的简单课程")
print(result.content)
```

### 学习路径规划

```python
result = skill.generate_path(
    student_id="ST001",
    target="后端开发工程师"
)
print(result.content)
```

## 配置说明

### 环境变量

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| DEBUG | 调试模式 | false |
| LLM_PROVIDER | 大模型提供商 | openai |
| LLM_API_KEY | API 密钥 | - |
| LLM_API_BASE | API 基础URL | - |
| TELEGRAM_BOT_TOKEN | Telegram 机器人Token | - |

### 配置文件

配置文件采用 JSON 格式，包含以下部分：

```json
{
  "llm": {
    "provider": "openai",
    "model": "gpt-4",
    "temperature": 0.7
  },
  "memory": {
    "backend_type": "file",
    "base_path": "./data/memory"
  },
  "channels": {
    "telegram": {
      "enabled": false,
      "bot_token": ""
    }
  }
}
```

## 开发指南

### 创建新技能

1. 在 `skills/` 目录下创建新文件
2. 继承或创建技能类
3. 实现必要的接口
4. 在智能体中注册技能

```python
from educlaw.core import SkillResult

class MySkill:
    def __init__(self, memory_store=None):
        self.memory_store = memory_store

    def execute(self, **kwargs) -> SkillResult:
        # 实现技能逻辑
        return SkillResult(
            success=True,
            content="执行成功",
            data={}
        )
```

### 创建新智能体

1. 在 `agents/` 目录下创建新文件
2. 继承 `ConversationalAgent` 或 `TaskAgent`
3. 实现必要的抽象方法
4. 在网关注册智能体

## 许可证

MIT License

## 联系方式

- 项目主页: [GitHub](https://github.com/your-repo/educlaw)
- 问题反馈: [Issues](https://github.com/your-repo/educlaw/issues)
