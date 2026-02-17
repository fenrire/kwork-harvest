import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    def __init__(
        self,
        slack_token: str | None = None,
        notion_token: str | None = None,
        database_id: str | None = None,
    ):
        self.slack_token = slack_token or os.getenv("SLACK_TOKEN", "")
        self.notion_token = notion_token or os.getenv("NOTION_TOKEN", "")
        self.database_id = database_id or os.getenv("NOTION_DATABASE_ID", "")

    def validate_slack(self) -> list[str]:
        errors: list[str] = []
        if not self.slack_token:
            errors.append("SLACK_TOKEN이 설정되지 않았습니다.")
        return errors

    def validate_notion(self) -> list[str]:
        errors: list[str] = []
        if not self.notion_token:
            errors.append("NOTION_TOKEN이 설정되지 않았습니다.")
        if not self.database_id:
            errors.append("NOTION_DATABASE_ID가 설정되지 않았습니다.")
        return errors

    def validate(self) -> list[str]:
        return self.validate_slack() + self.validate_notion()
