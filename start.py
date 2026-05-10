#!/usr/bin/env python
"""
EduClaw AgentScope 启动脚本

    使用方法:
    python start.py                        # 演示模式
    python start.py --interactive          # 交互模式 (需要 LLM 后端)
    python start.py --web                  # 启动 Web UI
    python start.py --web --port 5000      # 指定端口
    python start.py --model gpt-4o-mini --key sk-xxx --url https://api.openai.com/v1
    python start.py --skip-llm             # 跳过 LLM，直接测试工具调用

LLM 后端选项:
    Ollama (免费):  安装后运行: ollama pull qwen2.5:7b
    OpenAI:        提供 --key sk-xxx
    vLLM:          提供 --url http://your-server:8000/v1
"""

import asyncio
import sys
import io
import os
import argparse
from pathlib import Path

if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / ".env")

def parse_args():
    parser = argparse.ArgumentParser(description="EduClaw AgentScope 版本")
    parser.add_argument('--demo', action='store_true', help='运行演示模式')
    parser.add_argument('--interactive', '-i', action='store_true', help='运行交互模式')
    parser.add_argument('--skip-llm', action='store_true', help='跳过 LLM，直接调用工具（测试用）')
    parser.add_argument('--web', action='store_true', help='启动 Web UI')
    parser.add_argument('--port', type=int, default=8000, help='Web UI 端口 (默认 8000)')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Web UI 绑定地址')
    parser.add_argument('--model', type=str, default=None, help='模型名称')
    parser.add_argument('--key', type=str, default=None, help='API Key')
    parser.add_argument('--url', type=str, default=None, help='API Base URL')
    return parser.parse_args()


async def run_tool_demo():
    """无需 LLM 的工具测试"""
    from educlaw.tools.course import search_courses, generate_learning_path, recommend_courses
    from educlaw.tools.profile import generate_profile
    from educlaw.tools.warning import check_student_warning

    print("\n" + "=" * 50)
    print("EduClaw 工具直接测试模式 (无 LLM)")
    print("=" * 50)

    demos = [
        ("课程搜索: 编程", search_courses("编程")),
        ("学习路径: 后端", generate_learning_path("后端")),
        ("能力画像: demo_user", generate_profile("demo_user", "Demo", "CS", "2024")),
        ("学业预警: demo_user", check_student_warning("demo_user")),
        ("课程推荐: 编程", recommend_courses("编程")),
    ]

    for i, (name, coro) in enumerate(demos, 1):
        print(f"\n[演示 {i}] {name}")
        print("-" * 40)
        try:
            result = await coro
            text = result.content[0]['text'] if hasattr(result, 'content') else str(result)
            print(text)
        except Exception as e:
            print(f"错误: {e}")
        print("-" * 40)

    print("\n所有工具测试完成。要获得智能回复需要接入 LLM 后端。")


async def run_with_llm(args):
    """需要 LLM 后端的完整模式"""
    from educlaw.agents.edu_assistant import create_edu_agent
    from educlaw.main import run_demo, run_interactive

    model_name = args.model or os.getenv("LLM_MODEL", "qwen2.5:0.5b")
    api_key = args.key or os.getenv("LLM_API_KEY", "EMPTY")
    base_url = args.url or os.getenv("LLM_API_BASE", "http://localhost:11434/v1")

    print(f"正在连接模型: {model_name} @ {base_url}")
    print("(如需离线测试工具，请使用 --skip-llm)")

    try:
        agent = create_edu_agent(
            model_name=model_name,
            api_key=api_key,
            base_url=base_url,
        )
    except Exception as e:
        print(f"\n无法创建 Agent: {e}")
        print("\n请检查:")
        print("  1. LLM 后端是否在运行?")
        print(f"     当前配置: {base_url}")
        print("  2. 模型名称是否正确?")
        print(f"     当前模型: {model_name}")
        print("\n快速开始:")
        print("  - 安装 Ollama: https://ollama.com")
        print("  - 拉取模型: ollama pull qwen2.5:7b")
        print("  - 或使用 --skip-llm 直接测试工具")
        return

    try:
        if args.interactive:
            await run_interactive(agent)
        else:
            await run_demo(agent)
    except Exception as e:
        error_msg = str(e)
        if "connection" in error_msg.lower() or "connect" in error_msg.lower():
            print(f"\n无法连接到 LLM 后端 ({base_url})")
            print("请确保 LLM 服务已启动，或使用 --skip-llm 测试工具。")
        elif "404" in error_msg and "not found" in error_msg:
            print(f"\n模型 '{model_name}' 未找到。请先拉取模型:")
            print(f"  ollama pull {model_name}")
            print(f"\n或使用已安装的模型，例如:")
            available = await detect_ollama_models()
            if available:
                for m in available:
                    print(f"  python start.py --demo --model {m}")
            else:
                print("  (未检测到本地模型)")
            print(f"\n或离线测试工具: python start.py --skip-llm")
        else:
            print(f"\n运行出错: {e}")


async def detect_ollama_models() -> list:
    """检测本地 Ollama 可用模型"""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get("http://localhost:11434/api/tags")
            if r.status_code == 200:
                models = r.json().get("models", [])
                return [m["name"] for m in models]
    except Exception:
        pass
    return []


async def main_entry():
    args = parse_args()

    if args.skip_llm:
        await run_tool_demo()
        return

    if args.web:
        from educlaw.web import run_web
        run_web(host=args.host, port=args.port)
        return

    # 自动检测可用模型
    if not args.model:
        available = await detect_ollama_models()
        if available:
            # 优先选 7b+ 的模型，否则用第一个
            preferred = [m for m in available if "7b" in m.lower() or "8b" in m.lower()]
            default_model = preferred[0] if preferred else available[0]
            print(f"检测到本地模型: {', '.join(available)}")
            print(f"使用: {default_model}")
            args.model = default_model

    await run_with_llm(args)


if __name__ == "__main__":
    try:
        asyncio.run(main_entry())
    except KeyboardInterrupt:
        print("\nEduClaw 已停止。")
    except Exception as e:
        print(f"\n启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
