# slack-harvest

슬랙 메시지를 노션 데이터베이스에 채널/주제별로 자동 정리하는 CLI 도구입니다.

## 주요 기능

- Slack API로 채널 메시지 자동 수집 (본인 메시지만 필터링)
- 노션 데이터베이스에 채널별/날짜별 페이지 자동 생성
- 중복 업로드 방지 (동일 채널+날짜 스킵)
- dry-run 모드로 업로드 전 시뮬레이션

## 설치

```bash
pip install httpx python-dotenv
```

## 설정

### 1. Slack App 생성

1. [Slack API](https://api.slack.com/apps)에서 새 앱 생성
2. **OAuth & Permissions**에서 User Token Scopes 추가:
   - `channels:history` — 공개 채널 메시지 읽기
   - `channels:read` — 공개 채널 목록 조회
   - `groups:history` — 비공개 채널 메시지 읽기 (선택)
   - `groups:read` — 비공개 채널 목록 조회 (선택)
   - `users:read` — 사용자 이름 조회
3. 워크스페이스에 앱 설치 → **User OAuth Token** (`xoxp-...`) 복사

### 2. Notion Integration 생성

1. [My Integrations](https://www.notion.so/my-integrations)에서 생성
2. 노션 데이터베이스 페이지 → `···` → 연결 추가 → Integration 선택

### 3. 환경변수 설정

```bash
cp .env.example .env
```

`.env` 파일:
```
SLACK_TOKEN=xoxp-...           # Slack User OAuth Token
NOTION_TOKEN=secret_...        # Notion Integration Token
NOTION_DATABASE_ID=xxx         # 노션 데이터베이스 ID
```

> 데이터베이스 속성(제목, 채널, 날짜, 메시지 수)은 첫 업로드 시 자동으로 생성됩니다.

## 사용법

```bash
# 채널 목록 확인
python main.py channels

# 특정 채널 메시지를 노션에 업로드 (최근 30일)
python main.py fetch --channel general

# 여러 채널 한번에
python main.py fetch --channel general --channel random --channel dev

# 최근 7일만
python main.py fetch --channel general --days 7

# 업로드 시뮬레이션 (dry-run)
python main.py fetch --channel general --dry-run
```

## 프로젝트 구조

```
slack-harvest/
├── main.py                 # CLI 엔트리포인트
├── src/
│   ├── config.py           # 설정 관리
│   ├── models.py           # 데이터 모델
│   ├── slack_client.py     # Slack API 클라이언트
│   └── notion_uploader.py  # Notion API 업로더
├── pyproject.toml
├── .env.example
└── .gitignore
```
