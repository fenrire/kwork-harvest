from datetime import datetime

import httpx

from src.models import Channel, Message


class SlackClient:
    BASE_URL = "https://slack.com/api"

    def __init__(self, token: str):
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    def _get(self, method: str, params: dict | None = None) -> dict:
        response = httpx.get(
            f"{self.BASE_URL}/{method}",
            headers=self.headers,
            params=params or {},
            timeout=30,
        )
        data = response.json()
        if not data.get("ok"):
            raise RuntimeError(f"Slack API 오류 ({method}): {data.get('error', 'unknown')}")
        return data

    def _get_user_name(self, user_id: str, user_cache: dict[str, str]) -> str:
        if user_id in user_cache:
            return user_cache[user_id]
        try:
            data = self._get("users.info", {"user": user_id})
            name = data["user"].get("real_name") or data["user"].get("name", user_id)
        except RuntimeError:
            name = user_id
        user_cache[user_id] = name
        return name

    def list_channels(self, include_private: bool = False) -> list[dict]:
        """채널 목록 조회"""
        types = "public_channel,private_channel" if include_private else "public_channel"
        channels: list[dict] = []
        cursor = None

        while True:
            params: dict = {"types": types, "limit": 200, "exclude_archived": "true"}
            if cursor:
                params["cursor"] = cursor
            data = self._get("conversations.list", params)
            channels.extend(data.get("channels", []))
            cursor = data.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break

        return channels

    def fetch_messages(
        self,
        channel_id: str,
        channel_name: str,
        my_user_id: str | None = None,
        days: int = 30,
    ) -> Channel:
        """특정 채널의 메시지를 가져와 Channel 객체로 반환"""
        user_cache: dict[str, str] = {}
        messages: list[Message] = []
        cursor = None
        oldest = str(datetime.now().timestamp() - days * 86400)

        while True:
            params: dict = {"channel": channel_id, "limit": 200, "oldest": oldest}
            if cursor:
                params["cursor"] = cursor
            data = self._get("conversations.history", params)

            for msg in data.get("messages", []):
                # bot 메시지, 시스템 메시지 제외
                if msg.get("subtype") in ("bot_message", "channel_join", "channel_leave"):
                    continue
                user_id = msg.get("user", "")
                if my_user_id and user_id != my_user_id:
                    continue

                author = self._get_user_name(user_id, user_cache)
                ts = datetime.fromtimestamp(float(msg["ts"]))
                content = msg.get("text", "")

                messages.append(Message(
                    author=author,
                    content=content,
                    timestamp=ts,
                    channel=channel_name,
                ))

            cursor = data.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break

        messages.sort(key=lambda m: m.timestamp)
        return Channel(name=channel_name, messages=messages)

    def get_my_user_id(self) -> str:
        """현재 토큰의 사용자 ID 조회"""
        data = self._get("auth.test")
        return data["user_id"]
