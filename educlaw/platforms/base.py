"""Bot 平台适配器基类。"""

from abc import ABC, abstractmethod
from typing import Optional

from ..service.agent_service import AgentService, ChatResponse


class BotMessage:
    """平台无关的消息实体。"""

    def __init__(self, user_id: str, text: str, user_name: str = "",
                 conv_id: str = "", raw: dict = None):
        self.user_id = user_id
        self.text = text
        self.user_name = user_name
        self.conv_id = conv_id
        self.raw = raw or {}


class BaseBotAdapter(ABC):
    """Bot 平台适配器抽象基类。

    每个平台实现三个核心方法：
      start()      — 启动连接 (注册 webhook / 启动轮询)
      stop()       — 停止连接
      on_message() — 处理消息事件 (平台格式 → BotMessage → AgentService → 回复)
    """

    def __init__(self, agent_service: AgentService):
        self.agent = agent_service
        self._running = False

    @property
    def platform_name(self) -> str:
        return self.__class__.__name__.replace("BotAdapter", "").lower()

    @abstractmethod
    def start(self) -> None:
        ...

    @abstractmethod
    def stop(self) -> None:
        ...

    @abstractmethod
    def send_message(self, user_id: str, text: str,
                     actions: list = None, chart_data: dict = None) -> None:
        """发送回复消息到指定用户。"""
        ...

    def process_message(self, msg: BotMessage) -> ChatResponse:
        """通用消息处理管线：接收 BotMessage，调用 AgentService，返回 ChatResponse。"""
        return self.agent.chat(
            user_id=f"{self.platform_name}:{msg.user_id}",
            message=msg.text,
            conv_id=msg.conv_id,
            user_name=msg.user_name,
        )
