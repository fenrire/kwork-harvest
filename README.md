# kwork-harvest

카카오워크 대화를 노션 데이터베이스에 채널/주제별로 정리하는 CLI 도구입니다.

## 주요 기능

- **복사+붙여넣기 모드**: 카카오워크에서 대화를 복사해 터미널에 붙여넣으면 자동 파싱+업로드
- 텍스트 파일 파싱 (다양한 메시지 형식 지원)
- 특정 사용자(본인) 메시지만 필터링
- 노션 데이터베이스에 채널별/날짜별 페이지 자동 생성
- 중복 업로드 방지 (동일 채널+날짜 스킵)
- dry-run 모드로 업로드 전 시뮬레이션

## 설치

```bash
pip install httpx python-dotenv
```

## 설정

1. `.env` 파일 생성:

```bash
cp .env.example .env
```

2. `.env` 파일에 값 입력:

```
NOTION_TOKEN=secret_xxx        # Notion Integration 토큰
NOTION_DATABASE_ID=xxx         # 노션 데이터베이스 ID
MY_NAME=홍길동                  # 카카오워크에서 사용하는 본인 이름
```

3. **Notion Integration 생성**: [My Integrations](https://www.notion.so/my-integrations)에서 생성

4. **데이터베이스 연결**: 노션 데이터베이스 페이지 → `···` → 연결 추가 → Integration 선택

> 데이터베이스 속성(제목, 채널, 날짜, 메시지 수)은 첫 업로드 시 자동으로 생성됩니다.

## 사용법

### 방법 1: 복사+붙여넣기 (추천)

카카오워크에는 대화 내보내기 기능이 없으므로, 복사+붙여넣기 방식을 사용합니다.

```bash
# 1. 카카오워크에서 대화를 드래그하여 복사 (Ctrl+C / Cmd+C)
# 2. 터미널에서 아래 명령 실행
python main.py paste --channel "개발팀"

# 3. 터미널에 붙여넣기 (Ctrl+V / Cmd+V)
# 4. 빈 줄에서 Enter 두 번 → 자동 파싱 + 파일 저장

# 붙여넣기와 동시에 노션 업로드까지 하려면:
python main.py paste --channel "개발팀" --upload
```

### 방법 2: 텍스트 파일

```bash
# 대화 내용을 .txt 파일로 저장 → exports/ 폴더에 넣기
python main.py parse              # 파싱 결과 미리보기
python main.py upload --dry-run   # 업로드 시뮬레이션
python main.py upload             # 노션에 업로드
```

### 전체 명령어

| 명령 | 설명 |
|------|------|
| `python main.py guide` | 사용 가이드 |
| `python main.py paste --channel "이름"` | 복사+붙여넣기로 대화 수집 |
| `python main.py parse` | 파싱 결과 미리보기 |
| `python main.py upload` | 노션에 업로드 |

### 옵션

| 옵션 | 설명 |
|------|------|
| `--channel` | 채널/채팅방 이름 (paste 전용, 필수) |
| `--name` | 필터링할 본인 이름 (`.env`의 MY_NAME 대체) |
| `--dir` | 내보내기 파일 디렉토리 경로 (기본: `exports/`) |
| `--upload` | 붙여넣기 후 바로 노션 업로드 (paste 전용) |
| `--dry-run` | 실제 업로드 없이 시뮬레이션 |

## 지원하는 메시지 형식

| 형식 | 예시 |
|------|------|
| 기본 | `오전 9:30, 이름 : 메시지` |
| 카카오톡 형식1 | `[이름] [오후 2:30] 메시지` |
| 카카오톡 형식2 | `[2026-02-17 14:30:25] 이름 : 메시지` |
| ISO 날짜 형식 | `2026-02-17 14:30, 이름 : 메시지` |

## 프로젝트 구조

```
kwork-harvest/
├── main.py                 # CLI 엔트리포인트
├── src/
│   ├── config.py           # 설정 관리
│   ├── models.py           # 데이터 모델
│   ├── parser.py           # 메시지 파서
│   └── notion_uploader.py  # Notion API 업로더
├── exports/                # 내보내기 파일 저장 폴더
├── pyproject.toml
├── .env.example
└── .gitignore
```
