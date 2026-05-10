import sys, os
from pathlib import Path
sys.path.insert(0, str(Path("F:/eduClaw")))
from dotenv import load_dotenv
load_dotenv(".env")

from educlaw.web import app
import educlaw.web.app as wapp

# Simulate startup
wapp._init_llm()
print(f"_llm_available: {wapp._llm_available}")
print(f"_agent_model: {wapp._agent_model}")
print(f"_agent_url: {wapp._agent_url}")
print(f"_agent is not None: {wapp._agent is not None}")
print(f"last_error: {wapp.LLM_LAST_ERROR[:80] if wapp.LLM_LAST_ERROR else 'none'}")

# Test status endpoint
c = app.test_client()
r = c.get('/api/status')
d = r.get_json()
print(f"\n/api/status:")
print(f"  llm_available: {d['data']['llm_available']}")
print(f"  model: {d['data']['model']}")
print(f"  last_error: {d['data'].get('last_error', 'none')[:60]}")

if d['data']['llm_available']:
    print("\nLLM READY! python start.py --web will work.")
else:
    print(f"\nLLM FAILED: {d['data'].get('last_error', 'unknown')[:100]}")