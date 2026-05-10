"""
EduClaw AgentScope 版本 — 教育伴学智能体系统

使用方法:
    python -m educlaw.main              # 交互模式 (默认 Ollama)
    python -m educlaw.main --demo       # 演示模式
    python -m educlaw.main --model gpt-4o-mini --key sk-xxx --url https://api.openai.com/v1
"""

import asyncio
import sys
import io
import os
from pathlib import Path

# 确保控制台支持 UTF-8 输出
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

sys.path.insert(0, str(Path(__file__).parent.parent))

from agentscope.message import Msg
from educlaw.agents.edu_assistant import create_edu_agent


async def run_demo(agent):
    """运行演示模式"""
    demo_queries = [
        "你好，请介绍一下你的功能",
        "帮我搜索编程相关的课程",
        "我想成为后端开发工程师，请为我规划学习路径",
        "帮我查一下 demo_user 的能力画像",
        "帮我检查 demo_user 的学业预警情况",
        "推荐几门适合我的课程",
    ]

    print("\n" + "=" * 50)
    print("EduClaw AgentScope 演示模式")
    print("=" * 50)

    for i, query in enumerate(demo_queries, 1):
        print(f"\n[演示 {i}] 用户: {query}")
        print("-" * 40)
        sys.stdout.flush()
        try:
            response = await agent(Msg("user", query, "user"))
            content = response.get_text_content() if hasattr(response, 'get_text_content') else str(response)
            print(f"助手: {content}")
        except Exception as e:
            print(f"错误: {e}")
        print("-" * 40)
        sys.stdout.flush()

    print("\n演示完成！")


async def run_interactive(agent):
    """运行交互模式"""
    print("\n" + "=" * 50)
    print("EduClaw AgentScope 交互模式")
    print("输入您的问题，输入 'exit' 或 'quit' 退出")
    print("=" * 50 + "\n")

    while True:
        try:
            user_input = input("您: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n再见！")
            break

        if user_input.lower() in ('exit', 'quit', '退出'):
            print("再见！")
            break

        if not user_input:
            continue

        try:
            response = await agent(Msg("user", user_input, "user"))
            content = response.get_text_content() if hasattr(response, 'get_text_content') else str(response)
            print(f"\n助手: {content}\n")
        except Exception as e:
            print(f"\n错误: {e}\n")


def parse_args():
    import argparse
    parser = argparse.ArgumentParser(description="EduClaw AgentScope 版本")
    parser.add_argument('--demo', action='store_true', help='运行演示模式')
    parser.add_argument('--interactive', '-i', action='store_true', help='运行交互模式')
    parser.add_argument('--model', type=str, default=None, help='模型名称')
    parser.add_argument('--key', type=str, default=None, help='API Key')
    parser.add_argument('--url', type=str, default=None, help='API Base URL')
    return parser.parse_args()


async def main():
    args = parse_args()

    model_name = args.model or os.getenv("LLM_MODEL", "qwen2.5:7b")
    api_key = args.key or os.getenv("LLM_API_KEY", "EMPTY")
    base_url = args.url or os.getenv("LLM_API_BASE", "http://localhost:11434/v1")

    print(f"正在连接模型: {model_name} @ {base_url}")

    agent = create_edu_agent(
        model_name=model_name,
        api_key=api_key,
        base_url=base_url,
    )

    if args.demo:
        await run_demo(agent)
    else:
        await run_interactive(agent)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nEduClaw 已停止。")
    except Exception as e:
        print(f"\n启动失败: {e}")
        sys.exit(1)
