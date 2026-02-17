import argparse
import sys

from src.config import Config
from src.notion_uploader import NotionUploader
from src.parser import parse_directory


def cmd_guide(config: Config) -> None:
    """카카오워크 대화 내보내기 가이드"""
    exports_dir = config.exports_dir
    print("""
============================================
  카카오워크 대화 내보내기 가이드
============================================

[PC 앱에서 내보내기]

  1. 카카오워크 PC 앱을 엽니다
  2. 내보내기할 채팅방(채널/DM)에 들어갑니다
  3. 우측 상단 ≡ (메뉴) 버튼을 클릭합니다
  4. "대화 내보내기" 또는 "채팅 내보내기"를 선택합니다
  5. 텍스트(.txt) 형식으로 저장합니다
  6. 저장된 파일을 아래 디렉토리로 이동합니다:""")
    print(f"     {exports_dir.resolve()}/")
    print("""
[모바일 앱에서 내보내기]

  1. 카카오워크 모바일 앱을 엽니다
  2. 내보내기할 채팅방에 들어갑니다
  3. 우측 상단 ≡ (메뉴) 버튼을 탭합니다
  4. "대화 내보내기"를 선택합니다
  5. 파일 공유 또는 저장을 선택합니다
  6. PC로 옮긴 후 아래 디렉토리에 넣습니다:""")
    print(f"     {exports_dir.resolve()}/")
    print("""
[내보내기 후 실행 순서]

  python main.py parse              # 파싱 결과 미리보기
  python main.py upload --dry-run   # 업로드 시뮬레이션
  python main.py upload             # 실제 노션 업로드

[지원하는 파일 형식]

  - 오전 9:30, 이름 : 메시지
  - [이름] [오후 2:30] 메시지
  - [2026-02-17 14:30:25] 이름 : 메시지
  - 2026-02-17 14:30, 이름 : 메시지

[참고]

  - 채팅방마다 별도 파일로 내보내기됩니다
  - 파일 이름이 채널명으로 사용됩니다
  - 여러 채팅방을 한번에 처리할 수 있습니다
============================================
""")

    # 현재 exports 디렉토리 상태 표시
    txt_files = sorted(exports_dir.glob("*.txt")) if exports_dir.exists() else []
    if txt_files:
        print(f"현재 '{exports_dir}' 디렉토리에 {len(txt_files)}개 파일이 있습니다:")
        for f in txt_files:
            print(f"  - {f.name}")
    else:
        print(f"'{exports_dir}' 디렉토리에 아직 파일이 없습니다.")
        print("카카오워크에서 대화를 내보내기 한 후 위 디렉토리에 넣어주세요.")


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
            for msg in msgs[:3]:  # 날짜별 최대 3개만 미리보기
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
        description="카카오워크 내보내기 파일을 파싱하여 노션에 업로드합니다.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # guide 명령
    guide_parser = subparsers.add_parser("guide", help="카카오워크 대화 내보내기 가이드")
    guide_parser.add_argument("--dir", help="내보내기 파일 디렉토리 경로")

    # parse 명령
    parse_parser = subparsers.add_parser("parse", help="내보내기 파일 파싱 결과 미리보기")
    parse_parser.add_argument("--name", help="필터링할 본인 이름")
    parse_parser.add_argument("--dir", help="내보내기 파일 디렉토리 경로")

    # upload 명령
    upload_parser = subparsers.add_parser("upload", help="파싱 후 노션에 업로드")
    upload_parser.add_argument("--name", help="필터링할 본인 이름")
    upload_parser.add_argument("--dir", help="내보내기 파일 디렉토리 경로")
    upload_parser.add_argument("--dry-run", action="store_true", help="실제 업로드 없이 시뮬레이션")

    args = parser.parse_args()

    config = Config(
        my_name=getattr(args, "name", None),
        exports_dir=args.dir,
    )

    if args.command == "guide":
        cmd_guide(config)
    elif args.command == "parse":
        cmd_parse(config)
    elif args.command == "upload":
        cmd_upload(config, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
