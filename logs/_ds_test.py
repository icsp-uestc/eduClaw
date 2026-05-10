import sys, os
from pathlib import Path
sys.path.insert(0, str(Path("F:/eduClaw")))
from dotenv import load_dotenv
load_dotenv(".env")

print("=== Config ===")
print(f"MODEL: {os.getenv('LLM_MODEL')}")
print(f"BASE:  {os.getenv('LLM_API_BASE')}")
print(f"KEY:   {os.getenv('LLM_API_KEY')[:15]}***")

import educlaw.web.app as wapp
wapp._init_llm()

print(f"\n=== Result ===")
print(f"llm_available: {wapp._llm_available}")
print(f"agent_model: {wapp._agent_model}")
print(f"agent_url: {wapp._agent_url}")
print(f"agent_obj: {wapp._agent}")
print(f"last_error: {wapp.LLM_LAST_ERROR[:100] if wapp.LLM_LAST_ERROR else 'none'}")

if wapp._llm_available and wapp._agent:
    print("\nAgent created OK! Testing a chat call...")
    import asyncio
    from agentscope.message import Msg
    wapp._agent.memory.clear()
    async def test():
        r = await wapp._agent(Msg("user", "回复OK即可", "user"))
        t = r.get_text_content() if hasattr(r,'get_text_content') else str(r)
        print(f"Reply: {t[:100]}")
    asyncio.run(test())
else:
    print("\nFAILED - check the error above and fix credentials")