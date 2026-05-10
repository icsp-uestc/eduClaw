"""异步兼容工具 — 处理 asyncio.run 在已有事件循环中的调用问题。"""

import asyncio
from typing import Coroutine, Any


def run_async(coro: Coroutine) -> Any:
    """安全地运行异步协程，兼容已有事件循环的环境（如 Flask、Jupyter）。"""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # 没有运行中的事件循环，正常创建
        return asyncio.run(coro)

    # 已有事件循环，尝试使用 nest_asyncio
    try:
        import nest_asyncio
        nest_asyncio.apply(loop)
        return loop.run_until_complete(coro)
    except ImportError:
        pass

    # 回退：在新线程中运行
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(asyncio.run, coro)
        return future.result()
