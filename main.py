import argparse
import sys

from src.config import Config
from src.notion_uploader import NotionUploader
from src.slack_client import SlackClient


def cmd_channels(config: Config) -> None:
    """슬랙 채널 목록 조회"""
    errors = config.validate_slack()
    if errors:
        for e in errors:
            print(f"오류: {e}")
        sys.exit(1)

    client = SlackClient(config.slack_token)
    channels = client.list_channels(include_private=True)

    print(f"총 {len(channels)}개 채널:\n")
    for ch in sorted(channels, key=lambda c: c.get("name", "")):
        prefix = "🔒" if ch.get("is_private") else "#"
        print(f"  {prefix} {ch['name']}")


def cmd_fetch(config: Config, channel_names: list[str], days: int, dry_run: bool) -> None:
    """슬랙에서 메시지를 가져와 노션에 업로드"""
    slack_errors = config.validate_slack()
    if slack_errors:
        for e in slack_errors:
            print(f"오류: {e}")
        sys.exit(1)

    if not dry_run:
        notion_errors = config.validate_notion()
        if notion_errors:
            for e in notion_errors:
                print(f"오류: {e}")
            sys.exit(1)

    slack = SlackClient(config.slack_token)
    my_user_id = slack.get_my_user_id()

    # 채널 이름 → ID 매핑
    all_channels = slack.list_channels(include_private=True)
    channel_map = {ch["name"]: ch["id"] for ch in all_channels}

    # 대상 채널 결정
    if channel_names:
        targets = []
        for name in channel_names:
            name = name.lstrip("#")
            if name not in channel_map:
                print(f"경고: 채널 '{name}'을 찾을 수 없습니다. (python main.py channels 로 확인)")
            else:
                targets.append((name, channel_map[name]))
    else:
        print("--channel 옵션으로 채널을 지정하세요.")
        print("예: python main.py fetch --channel general --channel random")
        print("\n채널 목록 확인: python main.py channels")
        return

    if not targets:
        return

    # 메시지 수집
    collected = []
    for name, ch_id in targets:
        print(f"\n#{name} 메시지 수집 중 (최근 {days}일)...")
        channel = slack.fetch_messages(ch_id, name, my_user_id=my_user_id, days=days)
        if channel.messages:
            collected.append(channel)
            date_groups = channel.group_by_date()
            print(f"  {len(channel.messages)}개 메시지 ({len(date_groups)}일)")
        else:
            print("  메시지 없음")

    if not collected:
        print("\n수집된 메시지가 없습니다.")
        return

    # 노션 업로드
    if dry_run:
        print("\n[dry-run] 노션 업로드 시뮬레이션:")

    uploader = NotionUploader(
        token=config.notion_token,
        database_id=config.database_id,
    )
    uploader.upload_all(collected, dry_run=dry_run)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="슬랙 메시지를 노션에 정리합니다.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # channels
    subparsers.add_parser("channels", help="슬랙 채널 목록 조회")

    # fetch
    fetch_parser = subparsers.add_parser("fetch", help="슬랙에서 메시지를 가져와 노션에 업로드")
    fetch_parser.add_argument("--channel", action="append", dest="channels", help="대상 채널 (여러 개 가능)")
    fetch_parser.add_argument("--days", type=int, default=30, help="최근 N일 메시지 (기본: 30)")
    fetch_parser.add_argument("--dry-run", action="store_true", help="업로드 시뮬레이션")

    args = parser.parse_args()
    config = Config()

    if args.command == "channels":
        cmd_channels(config)
    elif args.command == "fetch":
        cmd_fetch(config, args.channels or [], args.days, args.dry_run)


if __name__ == "__main__":
    main()
