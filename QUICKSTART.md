# 🚀 Quick Start Guide

## 1️⃣ 프로젝트 설정

### 자동 설정 (권장)

```bash
# 설정 스크립트 실행
./setup.sh
```

### 수동 설정

```bash
# 1. 가상환경 생성 및 활성화
python3 -m venv venv
source venv/bin/activate

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 환경 변수 설정
cp env.example .env
# .env 파일을 편집하여 API 키 설정
```

## 2️⃣ API 키 설정

`.env` 파일을 편집하여 다음 API 키들을 설정하세요:

```bash
# 필수 API 키
ANTHROPIC_API_KEY=your_anthropic_api_key_here
NOTION_API_KEY=your_notion_api_key_here

# 선택적 API 키 (YouTube 크롤링용)
YOUTUBE_API_KEY=your_youtube_api_key_here
```

### API 키 획득 방법

#### Anthropic API 키

1. [Anthropic Console](https://console.anthropic.com/) 방문
2. 계정 생성 및 로그인
3. API 키 생성

#### Notion API 키

1. [Notion Developers](https://developers.notion.com/) 방문
2. "New integration" 생성
3. API 키 복사
4. 노션 데이터베이스에 integration 추가

## 3️⃣ 테스트 실행

```bash
# 가상환경 활성화
source venv/bin/activate

# 연결 테스트
news-crawler test
```

## 4️⃣ 사용 예제

### 패턴 기반 크롤링 (maeil-mail.kr)

```bash
# maeil-mail.kr 질문 1-10번 크롤링
news-crawler crawl-pattern \
  --base-url "https://www.maeil-mail.kr" \
  --start 1 \
  --end 10 \
  --notion-db "your-notion-database-id"
```

### 단일 URL 크롤링

```bash
# 단일 URL 크롤링
news-crawler crawl --url "https://example.com" --notion-db "your-database-id"
```

### YouTube 비디오 요약

```bash
# YouTube 비디오 요약
news-crawler summarize --url "https://youtube.com/watch?v=VIDEO_ID" --notion-db "your-database-id"
```

## 5️⃣ 대화형 실행

```bash
# 대화형 예제 실행
./run_example.sh
```

## 6️⃣ Python 스크립트 사용

```python
import asyncio
from news_crawler.core.config import Config
from news_crawler.core.crawler import Crawler

async def main():
    # 설정 로드
    config = Config.from_env()
    crawler = Crawler(config.dict())

    # 패턴 크롤링
    pattern_config = {
        'patterns': [{
            'type': 'numeric_range',
            'start': 1,
            'end': 10,
            'template': 'https://www.maeil-mail.kr/question/{number}'
        }]
    }

    contents = await crawler.crawl_pattern_urls(
        "https://www.maeil-mail.kr",
        pattern_config
    )

    # 노션 업로드
    page_ids = await crawler.summarize_and_upload(
        contents,
        "your-notion-database-id"
    )

    print(f"업로드된 항목: {len(page_ids)}개")

asyncio.run(main())
```

## 🔧 문제 해결

### 일반적인 문제들

1. **API 키 오류**

   ```bash
   # .env 파일 확인
   cat .env

   # 환경 변수 로드 확인
   source .env
   echo $ANTHROPIC_API_KEY
   ```

2. **의존성 설치 오류**

   ```bash
   # 가상환경 재생성
   rm -rf venv
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **권한 오류**
   ```bash
   # 실행 권한 부여
   chmod +x setup.sh
   chmod +x run_example.sh
   ```

## 📚 추가 정보

- [전체 문서](README.md)
- [설정 파일](config.yaml)
- [예제 스크립트](examples/maeil_mail_crawler.py)

## 🆘 도움이 필요하신가요?

문제가 발생하면 다음을 확인해보세요:

1. Python 3.8+ 설치 여부
2. API 키가 올바르게 설정되었는지
3. 인터넷 연결 상태
4. 방화벽 설정
