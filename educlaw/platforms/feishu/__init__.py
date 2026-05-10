"""飞书 Bot 适配器 — 基于飞书开放平台 API。"""

import json
import logging
import os
import threading
import time

import httpx

from ..base import BaseBotAdapter, BotMessage
from .card_builder import build_feishu_message

logger = logging.getLogger("feishu")

FEISHU_API = "https://open.feishu.cn/open-apis"


class FeishuBotAdapter(BaseBotAdapter):
    def __init__(self, agent_service):
        super().__init__(agent_service)
        self.app_id = os.getenv("FEISHU_APP_ID", "")
        self.app_secret = os.getenv("FEISHU_APP_SECRET", "")
        self._token = ""
        self._token_expires = 0
        self._token_lock = threading.Lock()
        self._http = httpx.Client(timeout=15)

    def start(self):
        if not self.app_id or not self.app_secret:
            raise RuntimeError(
                "飞书配置缺失，请在 .env 中设置 FEISHU_APP_ID 和 FEISHU_APP_SECRET")
        token = self._get_token()
        logger.info("Feishu Bot started (app_id=%s, token=%s...)", self.app_id, token[:10])
        self._running = True

    def stop(self):
        self._running = False
        self._http.close()
        logger.info("Feishu Bot stopped")

    def _get_token(self) -> str:
        """获取 tenant_access_token，带缓存和自动刷新。"""
        with self._token_lock:
            now = time.time()
            if self._token and now < self._token_expires - 120:
                return self._token

            resp = self._http.post(
                f"{FEISHU_API}/auth/v3/tenant_access_token/internal",
                json={"app_id": self.app_id, "app_secret": self.app_secret},
            )
            data = resp.json()
            if data.get("code") != 0:
                raise RuntimeError(f"飞书 Token 获取失败: {data}")
            self._token = data["tenant_access_token"]
            self._token_expires = now + data.get("expire", 7200)
            return self._token

    def handle_event(self, raw_event: dict) -> dict:
        """处理飞书事件回调。

        飞书会 POST JSON 到 webhook URL，格式为：
          {"schema": "2.0", "header": {...}, "event": {...}}

        支持的事件类型：
          - url_verification (首次配置验证)
          - im.message.receive_v1 (用户发送消息)
        """
        event_type = raw_event.get("type") or raw_event.get("header", {}).get("event_type", "")

        # URL 验证
        if event_type == "url_verification" or raw_event.get("challenge"):
            token = raw_event.get("token", "")
            challenge = raw_event.get("challenge", "")
            logger.info("Feishu URL verification: token=%s", token[:8] if token else "")
            return {"challenge": challenge}

        # 消息事件
        event = raw_event.get("event", raw_event)
        msg_type = event.get("message", {}).get("message_type", "")

        if event.get("type") == "im.message.receive_v1" or msg_type == "text":
            return self._on_message_received(event)

        logger.debug("Ignored event type: %s", event_type)
        return {"code": 0}

    def _on_message_received(self, event: dict) -> dict:
        """处理用户消息事件。"""
        message = event.get("message", event)
        text = json.loads(message.get("content", "{}")).get("text", "")
        if not text:
            return {"code": 0}

        sender = event.get("sender", {})
        user_id = sender.get("sender_id", {})
        if isinstance(user_id, dict):
            user_id = user_id.get("open_id", "")
        user_name = sender.get("sender_name", "") or user_id

        msg = BotMessage(
            user_id=user_id,
            text=text.strip(),
            user_name=user_name,
            raw=event,
        )

        logger.info("Feishu message from %s: %s", user_id, text[:80])

        # 调用 AgentService 处理
        response = self.process_message(msg)

        # 发送回复
        self.send_message(user_id, response.text, chart_data=response.chart_data)

        return {"code": 0}

    def send_message(self, user_id: str, text: str,
                     actions: list = None, chart_data: dict = None):
        """发送消息给飞书用户。"""
        token = self._get_token()
        payload = build_feishu_message(text, chart_data)
        payload["receive_id"] = user_id

        resp = self._http.post(
            f"{FEISHU_API}/im/v1/messages?receive_id_type=open_id",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )
        data = resp.json()
        if data.get("code") != 0:
            logger.error("Feishu send failed: %s", data)
        else:
            logger.info("Feishu message sent to %s", user_id)
