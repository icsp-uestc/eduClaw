import sys, os; sys.path.insert(0,'F:/eduClaw')
from dotenv import load_dotenv; load_dotenv("F:/eduClaw/.env")

from educlaw.web.app import app
c = app.test_client()

# 1. Clear endpoint
r = c.post('/api/chat/clear')
assert r.get_json()['ok']
print("[PASS] POST /api/chat/clear")

# 2. Skills count
r = c.get('/api/skills')
assert len(r.get_json()['data']) == 5
print("[PASS] /api/skills: 5")

# 3. Auth
r = c.get('/api/auth/status')
assert r.get_json()['data']['name'] == 'Demo'
print("[PASS] Auth: Demo")

print("\nALL PASSED - ready for python start.py --web")