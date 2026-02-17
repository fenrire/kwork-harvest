import argparse
import sys
from pathlib import Path

from src.config import Config
from src.notion_uploader import NotionUploader
from src.parser import parse_directory, parse_text


def cmd_guide(config: Config) -> None:
    """카카오워크 대화 수집 가이드"""
    print("""
============================================
  카카오워크 대화 → 노션 정리 가이드
============================================

[방법 1] 복사 + 붙여넣기 (추천)

  1. 카카오워크 PC 앱에서 채팅방을 엽니다
  2. 저장할 대화를 마우스로 드래그하여 선택합니다
  3. Ctrl+C (Mac: Cmd+C) 로 복사합니다
  4. 터미널에서 아래 명령을 실행합니다:

     python main.py paste --channel "채널이름"

  5. 터미널에 붙여넣기(Ctrl+V / Cmd+V) 합니다
  6. 빈 줄에서 Enter를 누르면 자동으로 파싱+업로드됩니다

[방법 2] 텍스트 파일 직접 저장

  1. 대화 내용을 복사하여 .txt 파일로 저장합니다
  2. exports/ 디렉토리에 넣습니다:""")
    print(f"     {config.exports_dir.resolve()}/")
    print("""
  3. 아래 명령으로 업로드합니다:

     python main.py upload

[지원하는 메시지 형식]

  - 오전 9:30, 이름 : 메시지
  - [이름] [오후 2:30] 메시지
  - [2026-02-17 14:30:25] 이름 : 메시지
  - 2026-02-17 14:30, 이름 : 메시지

[전체 명령어]

  python main.py guide              # 이 가이드
  python main.py paste --channel    # 복사+붙여넣기 모드
  python main.py parse              # 파싱 미리보기
  python main.py upload             # 파일에서 업로드
  python main.py upload --dry-run   # 업로드 시뮬레이션
============================================
""")


def cmd_paste(config: Config, channel_name: str, upload: bool, dry_run: bool) -> None:
    """클립보드에서 붙여넣기로 대화를 수집"""
    print(f"채널: {channel_name}")
    print("카카오워크에서 복사한 대화를 붙여넣으세요.")
    print("입력이 끝나면 빈 줄에서 Enter를 두 번 누르세요.")
    print("-" * 40)

    lines: list[str] = []
    empty_count = 0
    while True:
        try:
            line = input()
        except EOFError:
            break
        if line == "":
            empty_count += 1
            if empty_count >= 2:
                break
            lines.append(line)
        else:
            empty_count = 0
            lines.append(line)

    text = "\n".join(lines).strip()
    if not text:
        print("\n입력된 내용이 없습니다.")
        return

    # 파싱
    channel = parse_text(text, channel_name=channel_name, author_filter=config.my_name)

    if not channel.messages:
        print(f"\n파싱된 메시지가 없습니다.")
        print(f"  - MY_NAME('{config.my_name}')이 카카오워크 이름과 일치하는지 확인하세요.")
        print("  - 메시지 형식이 지원되는 형식인지 확인하세요 (python main.py guide)")
        return

    # 결과 미리보기
    date_groups = channel.group_by_date()
    print(f"\n{channel.name}: {len(channel.messages)}개 메시지 파싱 완료")
    for date_str, msgs in sorted(date_groups.items()):
        print(f"  {date_str}: {len(msgs)}개")

    # 파일로 저장
    save_path = config.exports_dir / f"{channel_name}.txt"
    if save_path.exists():
        # 기존 파일에 추가
        with open(save_path, "a", encoding="utf-8") as f:
            f.write("\n" + text + "\n")
        print(f"\n기존 파일에 추가: {save_path}")
    else:
        config.exports_dir.mkdir(parents=True, exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            f.write(f"{channel_name} 대화\n")
            f.write(text + "\n")
        print(f"\n파일 저장: {save_path}")

    # 업로드
    if upload:
        errors = config.validate()
        if errors:
            print("설정 오류:")
            for e in errors:
                print(f"  - {e}")
            sys.exit(1)

        uploader = NotionUploader(
            token=config.notion_token,
            database_id=config.database_id,
        )
        uploader.upload_all([channel], dry_run=dry_run)
    else:
        print("\n노션 업로드: python main.py upload")


def cmd_parse(config: Config) -> None:
    """내보내기 파일 파싱 결과 미리보기"""
    channels = parse_directory(config.exports_dir, author_filter=config.my_name)

    if not channels:
        print("파싱된 메시지가 없습니다.")
        print(f"  - '{config.exports_dir}' 디렉토리에 .txt 파일이 있는지 확인하세요.")
        print(f"  - MY_NAME('{config.my_name}')이 카카오워크 이름과 일치하는지 확인하세요.")
        return

    total = 0
    for ch in channels:
        date_groups = ch.group_by_date()
        print(f"\n채널: {ch.name} ({len(ch.messages)}개 메시지)")
        for date_str, msgs in sorted(date_groups.items()):
            print(f"  {date_str}: {len(msgs)}개")
            for msg in msgs[:3]:
                preview = msg.content[:80] + ("..." if len(msg.content) > 80 else "")
                print(f"    [{msg.time_str}] {preview}")
            if len(msgs) > 3:
                print(f"    ... 외 {len(msgs) - 3}개")
        total += len(ch.messages)

    print(f"\n총 {len(channels)}개 채널, {total}개 메시지")


def cmd_upload(config: Config, dry_run: bool = False) -> None:
    """파싱 후 노션에 업로드"""
    if not dry_run:
        errors = config.validate()
        if errors:
            print("설정 오류:")
            for e in errors:
                print(f"  - {e}")
            sys.exit(1)

    channels = parse_directory(config.exports_dir, author_filter=config.my_name)

    if not channels:
        print("업로드할 메시지가 없습니다.")
        return

    uploader = NotionUploader(
        token=config.notion_token,
        database_id=config.database_id,
    )
    uploader.upload_all(channels, dry_run=dry_run)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="카카오워크 대화를 노션에 정리합니다.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # guide
    guide_parser = subparsers.add_parser("guide", help="사용 가이드")
    guide_parser.add_argument("--dir", help="내보내기 파일 디렉토리 경로")

    # paste
    paste_parser = subparsers.add_parser("paste", help="복사+붙여넣기로 대화 수집")
    paste_parser.add_argument("--channel", required=True, help="채널/채팅방 이름")
    paste_parser.add_argument("--name", help="필터링할 본인 이름")
    paste_parser.add_argument("--dir", help="내보내기 파일 디렉토리 경로")
    paste_parser.add_argument("--upload", action="store_true", help="붙여넣기 후 바로 노션 업로드")
    paste_parser.add_argument("--dry-run", action="store_true", help="업로드 시뮬레이션")

    # parse
    parse_parser = subparsers.add_parser("parse", help="파싱 결과 미리보기")
    parse_parser.add_argument("--name", help="필터링할 본인 이름")
    parse_parser.add_argument("--dir", help="내보내기 파일 디렉토리 경로")

    # upload
    upload_parser = subparsers.add_parser("upload", help="노션에 업로드")
    upload_parser.add_argument("--name", help="필터링할 본인 이름")
    upload_parser.add_argument("--dir", help="내보내기 파일 디렉토리 경로")
    upload_parser.add_argument("--dry-run", action="store_true", help="업로드 시뮬레이션")

    args = parser.parse_args()

    config = Config(
        my_name=getattr(args, "name", None),
        exports_dir=getattr(args, "dir", None),
    )

    if args.command == "guide":
        cmd_guide(config)
    elif args.command == "paste":
        cmd_paste(config, args.channel, args.upload, args.dry_run)
    elif args.command == "parse":
        cmd_parse(config)
    elif args.command == "upload":
        cmd_upload(config, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
