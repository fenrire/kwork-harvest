import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


class Config:
    def __init__(
        self,
        notion_token: str | None = None,
        database_id: str | None = None,
        my_name: str | None = None,
        exports_dir: str | None = None,
    ):
        self.notion_token = notion_token or os.getenv("NOTION_TOKEN", "")
        self.database_id = database_id or os.getenv("NOTION_DATABASE_ID", "")
        self.my_name = my_name or os.getenv("MY_NAME", "")
        self.exports_dir = Path(exports_dir) if exports_dir else Path("exports")

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.notion_token:
            errors.append("NOTION_TOKEN이 설정되지 않았습니다.")
        if not self.database_id:
            errors.append("NOTION_DATABASE_ID가 설정되지 않았습니다.")
        if not self.my_name:
            errors.append("MY_NAME이 설정되지 않았습니다.")
        if not self.exports_dir.exists():
            errors.append(f"내보내기 디렉토리가 존재하지 않습니다: {self.exports_dir}")
        return errors
