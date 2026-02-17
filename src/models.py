from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Message:
    author: str
    content: str
    timestamp: datetime
    channel: str

    @property
    def date_str(self) -> str:
        return self.timestamp.strftime("%Y-%m-%d")

    @property
    def time_str(self) -> str:
        return self.timestamp.strftime("%H:%M")


@dataclass
class Channel:
    name: str
    messages: list[Message] = field(default_factory=list)

    def filter_by_author(self, author: str) -> "Channel":
        filtered = [m for m in self.messages if m.author == author]
        return Channel(name=self.name, messages=filtered)

    def group_by_date(self) -> dict[str, list[Message]]:
        groups: dict[str, list[Message]] = {}
        for msg in self.messages:
            groups.setdefault(msg.date_str, []).append(msg)
        return groups
