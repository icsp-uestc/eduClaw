# AGENTS.md — EduClaw

## Framework
- **AgentScope >= 1.0.0** is the agent framework — not LangChain, not LlamaIndex.
- Agent is a `ReActAgent` using `OpenAIChatModel` (OpenAI-compatible API), `InMemoryMemory`, and `Toolkit`.
- Doc reference: [AgentScope docs](https://doc.agentscope.io)

## Entry points
```
python start.py                    # auto-detects Ollama models, interactive
python start.py --demo             # runs demo queries with LLM
python start.py --skip-llm         # runs tool functions directly, no LLM needed
python start.py --web              # launch Web UI (default http://0.0.0.0:8000)
python start.py --web --port 5000  # Web UI on custom port
python -m educlaw.main --demo      # same as above from package
python -m educlaw.main --model qwen2.5:7b --key EMPTY --url http://localhost:11434/v1
```

## How to run a focused test
```bash
python start.py --skip-llm          # fastest smoke test, no LLM required
python start.py --demo --model gpt-4o-mini --key sk-xxx --url https://api.openai.com/v1
```
`--skip-llm` exercises all 5 tool functions (course search, learning path, profile, warning, recommendation) directly and is the quickest way to verify tool code changes.

## Architecture
```
educlaw/
  skills/         # File-based skill modules (auto-discovered by SkillRegistry)
    __init__.py   # SkillRegistry — discovers, lists, runs skills
    course_search/           # SKILL.md + __init__.py (toolkit + run())
    course_recommend/
    learning_path/
    student_profile/
    academic_warning/
  agents/         # ReActAgent creation + auto-generated SYS_PROMPT
  models/         # Dataclasses: Course, StudentProfile, WarningAlert, etc.
  core/           # NL2SQLParser (keyword extraction) + mock_data (COURSE_DATABASE, PATH_DATABASE)
  memory/         # FileMemoryBackend (file-based persistent storage)
  web/            # Flask web UI (app.py, templates/, static/)
  configs/        # model_configs.json (preconfigured Ollama/vLLM/OpenAI profiles)
  utils/          # logger.py (colored console + file logging)
```

- `educlaw/tools/` is the **legacy** tool layer — new skills go in `educlaw/skills/`.
- The agent (`edu_assistant.py`) auto-generates SYS_PROMPT from `list_skills()`.

## Data is all mock
- `core/mock_data.py`: 10 hardcoded courses, 3 learning paths.
- Skill implementations use hardcoded data (no real database).

## Adding a new skill
1. Create `educlaw/skills/<skill_id>/` directory with:
   - `SKILL.md` — documentation (name, description, trigger keywords, workflow)
   - `__init__.py` — must export: `skill_id`, `skill_name`, `skill_icon`, `skill_desc`, `toolkit`, `run(prompt)`
2. That's it. The `SkillRegistry` auto-discovers it on next import.
3. The Web UI popover automatically picks up new skills from `/api/skills`.
4. The agent's SYS_PROMPT auto-updates with the new skill.

## Environment
- `.env` is loaded via `python-dotenv` (used in start.py).
- Conda env path from `.claude/settings.local.json`: `/e/miniconda3/envs/educlaw/`.
- Default Ollama URL: `http://localhost:11434/v1` (standard Ollama port).
- API key for local models is `"EMPTY"`.

## Things that don't exist yet
- No test suite (pytest is listed in requirements.txt but no test files exist).
- No lint/formatter/typecheck config.
- No CI/CD workflows.
- No git repo initialized.
