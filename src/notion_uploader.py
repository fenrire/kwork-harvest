import httpx

from src.models import Channel, Message

NOTION_VERSION = "2022-06-28"
BASE_URL = "https://api.notion.com/v1"


class NotionUploader:
    def __init__(self, token: str, database_id: str):
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        }
        self.database_id = database_id

    def _request(self, method: str, path: str, json_data: dict | None = None) -> dict:
        url = f"{BASE_URL}/{path}"
        response = httpx.request(method, url, headers=self.headers, json=json_data, timeout=30)
        response.raise_for_status()
        return response.json()

    def setup_database(self) -> None:
        """데이터베이스에 필요한 속성 추가"""
        db = self._request("GET", f"databases/{self.database_id}")
        existing_props = set(db.get("properties", {}).keys())

        props_to_add: dict = {}
        if "제목" not in existing_props:
            # 기본 title 속성 이름을 '제목'으로 변경
            for name, prop in db.get("properties", {}).items():
                if prop.get("type") == "title" and name != "제목":
                    props_to_add[name] = {"name": "제목"}
                    break
        if "채널" not in existing_props:
            props_to_add["채널"] = {"select": {"options": []}}
        if "날짜" not in existing_props:
            props_to_add["날짜"] = {"date": {}}
        if "메시지 수" not in existing_props:
            props_to_add["메시지 수"] = {"number": {"format": "number"}}

        if props_to_add:
            self._request("PATCH", f"databases/{self.database_id}", {"properties": props_to_add})
            print("데이터베이스 속성 설정 완료")

    def _find_existing_page(self, channel_name: str, date_str: str) -> str | None:
        """같은 채널+날짜의 기존 페이지가 있는지 확인"""
        response = self._request("POST", f"databases/{self.database_id}/query", {
            "filter": {
                "and": [
                    {"property": "채널", "select": {"equals": channel_name}},
                    {"property": "날짜", "date": {"equals": date_str}},
                ]
            }
        })
        results = response.get("results", [])
        if results:
            return results[0]["id"]
        return None

    def _build_message_blocks(self, messages: list[Message]) -> list[dict]:
        """메시지 목록을 Notion 블록 리스트로 변환"""
        blocks: list[dict] = []
        for msg in messages:
            text = f"[{msg.time_str}] {msg.content}"
            if len(text) > 2000:
                text = text[:1997] + "..."
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {"content": text},
                        }
                    ]
                },
            })
        return blocks

    def upload_channel(self, channel: Channel, dry_run: bool = False) -> int:
        """채널의 메시지를 날짜별로 노션 페이지에 업로드. 생성된 페이지 수를 반환."""
        date_groups = channel.group_by_date()
        created_count = 0

        for date_str, messages in sorted(date_groups.items()):
            title = f"{channel.name} - {date_str}"

            if dry_run:
                print(f"  [dry-run] 페이지 생성: \"{title}\" ({len(messages)}개 메시지)")
                created_count += 1
                continue

            # 중복 체크
            existing_id = self._find_existing_page(channel.name, date_str)
            if existing_id:
                print(f"  [스킵] 이미 존재: \"{title}\"")
                continue

            # 블록 생성 (Notion API는 한번에 최대 100블록)
            all_blocks = self._build_message_blocks(messages)
            first_batch = all_blocks[:100]

            page = self._request("POST", "pages", {
                "parent": {"database_id": self.database_id},
                "properties": {
                    "제목": {
                        "title": [{"type": "text", "text": {"content": title}}]
                    },
                    "채널": {"select": {"name": channel.name}},
                    "날짜": {"date": {"start": date_str}},
                    "메시지 수": {"number": len(messages)},
                },
                "children": first_batch,
            })

            # 100개 초과 블록은 추가로 append
            remaining = all_blocks[100:]
            page_id = page["id"]
            while remaining:
                batch = remaining[:100]
                remaining = remaining[100:]
                self._request("PATCH", f"blocks/{page_id}/children", {"children": batch})

            print(f"  [생성] \"{title}\" ({len(messages)}개 메시지)")
            created_count += 1

        return created_count

    def upload_all(self, channels: list[Channel], dry_run: bool = False) -> None:
        """모든 채널을 업로드"""
        if not dry_run:
            self.setup_database()

        total_pages = 0
        for channel in channels:
            print(f"\n채널: {channel.name} ({len(channel.messages)}개 메시지)")
            count = self.upload_channel(channel, dry_run=dry_run)
            total_pages += count

        mode = "[dry-run] " if dry_run else ""
        print(f"\n{mode}완료: 총 {total_pages}개 페이지 처리")
