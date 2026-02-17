import re
from datetime import datetime
from pathlib import Path

from src.models import Channel, Message

# 카카오워크 내보내기 파일 형식 패턴
# 예: "2026년 2월 17일 오전 10:30, 홍길동 : 안녕하세요"
# 또는: "2026-02-17 10:30:00, 홍길동 : 안녕하세요"
DATE_LINE_PATTERN = re.compile(
    r"^-+\s*(\d{4}년\s*\d{1,2}월\s*\d{1,2}일)\s*.*-+$"
)

MESSAGE_PATTERN = re.compile(
    r"^(오전|오후)?\s*(\d{1,2}:\d{2})\s*,?\s*(.+?)\s*:\s*(.+)$"
)

# 대체 형식: "2026-02-17 10:30, 홍길동 : 메시지"
ALT_MESSAGE_PATTERN = re.compile(
    r"^(\d{4}-\d{2}-\d{2})\s+(\d{1,2}:\d{2}(?::\d{2})?)\s*,?\s*(.+?)\s*:\s*(.+)$"
)

# 카카오톡 형식: "[2026-02-17 14:30:25] 홍길동 : 메시지"
KAKAO_BRACKET_PATTERN = re.compile(
    r"^\[(\d{4}-\d{2}-\d{2})\s+(\d{1,2}:\d{2}(?::\d{2})?)\]\s*(.+?)\s*:\s*(.+)$"
)

# 카카오톡 형식2: "[홍길동] [오후 2:30] 메시지"
KAKAO_NAME_FIRST_PATTERN = re.compile(
    r"^\[(.+?)\]\s*\[(오전|오후)\s*(\d{1,2}:\d{2})\]\s*(.+)$"
)

# 채널 정보 헤더 패턴
CHANNEL_HEADER_PATTERN = re.compile(
    r"^(?:#?\s*)?(.+?)(?:\s+대화\s+내보내기|\s+채팅|\s+님과\s+카카오톡).*$"
)


def _parse_korean_date(date_str: str) -> str:
    """'2026년 2월 17일' 형식을 '2026-02-17'로 변환"""
    match = re.match(r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일", date_str)
    if match:
        y, m, d = match.groups()
        return f"{y}-{int(m):02d}-{int(d):02d}"
    return date_str


def _parse_time(period: str | None, time_str: str) -> str:
    """오전/오후 + 시:분 을 24시간 형식으로 변환"""
    parts = time_str.split(":")
    hour = int(parts[0])
    minute = parts[1]

    if period == "오후" and hour != 12:
        hour += 12
    elif period == "오전" and hour == 12:
        hour = 0

    return f"{hour:02d}:{minute}"


def _parse_lines(lines: list[str], default_channel: str) -> Channel:
    """텍스트 줄 목록을 파싱하여 Channel 객체로 반환"""
    channel_name = default_channel
    messages: list[Message] = []
    current_date: str | None = None

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue

        # 첫 몇 줄에서 채널 이름 추출 시도
        if i < 5:
            header_match = CHANNEL_HEADER_PATTERN.match(line)
            if header_match:
                channel_name = header_match.group(1).strip()
                continue

        # 날짜 구분선
        date_match = DATE_LINE_PATTERN.match(line)
        if date_match:
            current_date = _parse_korean_date(date_match.group(1))
            continue

        # 카카오톡 형식: "[2026-02-17 14:30:25] 홍길동 : 메시지"
        bracket_match = KAKAO_BRACKET_PATTERN.match(line)
        if bracket_match:
            date_str, time_str, author, content = bracket_match.groups()
            fmt = "%Y-%m-%d %H:%M:%S" if len(time_str) > 5 else "%Y-%m-%d %H:%M"
            ts = datetime.strptime(f"{date_str} {time_str}", fmt)
            messages.append(Message(
                author=author.strip(),
                content=content.strip(),
                timestamp=ts,
                channel=channel_name,
            ))
            continue

        # 카카오톡 형식2: "[홍길동] [오후 2:30] 메시지"
        name_first_match = KAKAO_NAME_FIRST_PATTERN.match(line)
        if name_first_match and current_date:
            author, period, time_str, content = name_first_match.groups()
            time_24 = _parse_time(period, time_str)
            ts = datetime.strptime(f"{current_date} {time_24}", "%Y-%m-%d %H:%M")
            messages.append(Message(
                author=author.strip(),
                content=content.strip(),
                timestamp=ts,
                channel=channel_name,
            ))
            continue

        # 대체 형식 메시지 (날짜 포함)
        alt_match = ALT_MESSAGE_PATTERN.match(line)
        if alt_match:
            date_str, time_str, author, content = alt_match.groups()
            fmt = "%Y-%m-%d %H:%M:%S" if len(time_str) > 5 else "%Y-%m-%d %H:%M"
            ts = datetime.strptime(f"{date_str} {time_str}", fmt)
            messages.append(Message(
                author=author.strip(),
                content=content.strip(),
                timestamp=ts,
                channel=channel_name,
            ))
            continue

        # 기본 형식 메시지 (시간 + 이름 : 내용)
        msg_match = MESSAGE_PATTERN.match(line)
        if msg_match and current_date:
            period, time_str, author, content = msg_match.groups()
            time_24 = _parse_time(period, time_str)
            ts = datetime.strptime(f"{current_date} {time_24}", "%Y-%m-%d %H:%M")
            messages.append(Message(
                author=author.strip(),
                content=content.strip(),
                timestamp=ts,
                channel=channel_name,
            ))
            continue

        # 이전 메시지의 여러 줄 내용 (줄바꿈된 메시지)
        if messages and line and not date_match:
            messages[-1].content += "\n" + line

    return Channel(name=channel_name, messages=messages)


def parse_file(file_path: Path) -> Channel:
    """카카오워크 내보내기 텍스트 파일 하나를 파싱하여 Channel 객체로 반환"""
    text = file_path.read_text(encoding="utf-8")
    return _parse_lines(text.splitlines(), default_channel=file_path.stem)


def parse_text(text: str, channel_name: str, author_filter: str | None = None) -> Channel:
    """텍스트 문자열을 파싱하여 Channel 객체로 반환 (붙여넣기 모드용)"""
    channel = _parse_lines(text.splitlines(), default_channel=channel_name)
    if author_filter:
        channel = channel.filter_by_author(author_filter)
    return channel


def parse_directory(directory: Path, author_filter: str | None = None) -> list[Channel]:
    """디렉토리 내 모든 .txt 파일을 파싱하여 Channel 목록으로 반환"""
    channels: list[Channel] = []

    txt_files = sorted(directory.glob("*.txt"))
    if not txt_files:
        print(f"경고: '{directory}'에 .txt 파일이 없습니다.")
        return channels

    for file_path in txt_files:
        channel = parse_file(file_path)
        if author_filter:
            channel = channel.filter_by_author(author_filter)
        if channel.messages:
            channels.append(channel)

    return channels
