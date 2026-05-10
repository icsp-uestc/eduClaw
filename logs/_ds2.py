import sys, os
from pathlib import Path
sys.path.insert(0, str(Path("F:/eduClaw")))
from dotenv import load_dotenv
load_dotenv(".env")

print("=== Config ===")
print(f"MODEL: {os.getenv('LLM_MODEL')}")
print(f"BASE:  {os.getenv('LLM_API_BASE')}")
print(f"KEY:   {os.getenv('LLM_API_KEY')[:15]}***")

# Import the actual module file
import importlib.util
spec = importlib.util.spec_from_file_location("app", "F:/eduClaw/educlaw/web/app.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

mod._init_llm()

print(f"\n=== Result ===")
print(f"llm_available: {mod._llm_available}")
print(f"agent_model: {mod._agent_model}")
print(f"agent_url: {mod._agent_url}")
print(f"last_error: {mod.LLM_LAST_ERROR[:150] if mod.LLM_LAST_ERROR else 'none'}")

if mod._llm_available and mod._agent is not None:
    print("\nAgent created! Testing chat...")
    mod._agent.memory.clear()
    import asyncio
    from agentscope.message import Msg
    async def t():
        r = await mod._agent(Msg("user", "say ok", "user"))
        print(f"Reply: {r.get_text_content()[:200]}")
    asyncio.run(t())
else:
    print(f"\nFAILED: agent={mod._agent}, available={mod._llm_available}")