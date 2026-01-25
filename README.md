# Blog Agents - AI 블로그 콘텐츠 생성 시스템

키워드를 입력하면 자동으로 고품질 블로그 콘텐츠를 생성하는 Python 기반 멀티 에이전트 시스템입니다.

## 프로젝트 개요

이 시스템은 4개의 전문화된 AI 에이전트가 협력하여 키워드로부터 완성도 높은 블로그 포스트를 자동으로 생성합니다. Claude API의 웹 검색 기능을 활용하여 최신 정보를 수집하고, 사용자의 글쓰기 스타일을 학습하여 일관된 톤으로 콘텐츠를 작성합니다.

## 동작 방식

1. **검색 단계 (PostSearcher)**: 키워드를 기반으로 Claude의 `web_search` 도구를 사용하여 관련 게시글을 검색하고, AI가 자동으로 관련성 높은 상위 결과를 선별합니다.

2. **기획 단계 (BlogPlanner)**: 선별된 게시글을 분석하여 핵심 주제와 개념을 파악하고, 3-7개 섹션으로 구성된 구조화된 블로그 개요를 작성합니다.

3. **작성 단계 (BlogWriter)**: 참조 문서에서 학습한 글쓰기 톤을 적용하여, 작성된 개요를 바탕으로 완성도 높은 블로그 포스트를 생성합니다.

4. **검토 단계 (BlogReviewer)**: 오탈자 및 중복 표현을 검사하고, 형식적인 말투를 개선하며, 출처와 비교하여 신뢰도를 검증합니다. Adaptive Learning을 통해 글의 지식을 학습하여 이후 작성에 활용합니다.

## 아키텍처

![Architecture Diagram](assets/architecture.png)

시스템은 Orchestrator가 중심이 되어 4개의 전문 에이전트를 조율합니다. 각 에이전트는 독립적으로 동작하며, 체크포인트 시스템을 통해 작업 중단 시에도 이전 상태에서 재개할 수 있습니다. Claude API를 통해 웹 검색과 AI 생성을 모두 처리하므로 추가 외부 API가 필요하지 않습니다.

## 주요 개선사항

### 1. BlogReviewer 에이전트 추가
- **오탈자 자동 검사 및 수정**: 맞춤법, 중복 표현, 문법 오류를 자동으로 감지하고 수정
- **말투 개선**: "~~하죠", "~~합니다" 등 형식적이고 딱딱한 표현을 자연스럽고 인간친화적인 표현으로 개선
- **신뢰도 검증**: 작성된 콘텐츠를 원본 출처와 비교하여 사실 관계 검증

### 2. Adaptive Learning 스킬
- **지식 학습 시스템**: 작성된 블로그의 내용을 학습하여 이후 콘텐츠 생성 시 활용
- **컨텍스트 누적**: 여러 블로그를 생성하면서 도메인 지식을 지속적으로 축적
- **품질 향상**: 학습된 지식을 바탕으로 더욱 전문적이고 정확한 콘텐츠 생성

### 3. Claude Web Search 통합
- **단일 API 통합**: Anthropic API 하나로 검색과 생성 모두 처리
- **AI 기반 필터링**: Claude가 직접 검색 결과의 품질과 관련성을 평가
- **비용 절감**: 별도의 검색 API(Google, Bing 등) 구독 불필요

### 4. 톤 학습 시스템
- **스타일 분석**: 참조 문서에서 글쓰기 톤, 어휘, 문장 구조 자동 학습
- **일관성 유지**: 모든 생성 콘텐츠에 동일한 글쓰기 스타일 적용
- **커스터마이징**: 원하는 톤의 샘플 문서만 제공하면 자동으로 학습

## 빠른 시작

1. 저장소 클론:
```bash
git clone <repository-url>
cd news-crawler
```

2. 가상 환경 생성:
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. 의존성 설치:
```bash
pip install -r blog_agents_requirements.txt
```

4. 환경 설정:
```bash
cp .env.example .env
# .env 파일을 편집하여 Anthropic API 키 추가
```

`.env` 파일 예시:
```env
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

5. 시스템 설정 (선택):
```bash
# config.yaml을 편집하여 에이전트 동작 커스터마이징
```

## 빠른 시작

### 1. 블로그 포스트 생성

```bash
python -m blog_agents.cli.blog_cli generate --keywords "Python asyncio 모범 사례"
```

### 2. 글쓰기 톤 분석 (선택사항)

```bash
python -m blog_agents.cli.blog_cli analyze-tone --file references/reference.md
```

### 3. 검색만 실행

```bash
python -m blog_agents.cli.blog_cli search-only --keywords "머신러닝"
```

실행하면 `outputs/` 디렉토리에 생성된 블로그와 검토 결과가 저장됩니다.

## Python API 사용 예시

```python
import asyncio
from blog_agents.core.orchestrator import BlogOrchestrator

async def generate_blog():
    orchestrator = BlogOrchestrator()
    result = await orchestrator.generate_blog("Python 테스팅")
    print(f"블로그 저장 위치: {result['blog_file']}")

asyncio.run(generate_blog())
```

## 프로젝트 구조

```
news-crawler/
├── blog_agents/
│   ├── agents/          # PostSearcher, BlogPlanner, BlogWriter, BlogReviewer
│   ├── core/            # Orchestrator, BaseAgent, Communication
│   ├── search/          # Claude web_search 통합
│   ├── skills/          # ToneLearner, AdaptiveLearner
│   ├── config/          # 설정 관리
│   ├── utils/           # 파일 관리, 검증 등
│   └── cli/             # CLI 인터페이스
├── outputs/             # 생성된 블로그 및 체크포인트
├── references/          # 톤 학습용 참조 문서
├── config.yaml          # 시스템 설정
└── .env                 # API 키
```

---

## 설치 및 실행

### 사전 요구사항
- Python 3.9 이상
- Anthropic API 키

### 설치

```bash
# 1. 저장소 클론
git clone <repository-url>
cd news-crawler

# 2. 가상 환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. 의존성 설치
pip install -r blog_agents_requirements.txt

# 4. 환경 변수 설정
cp .env.example .env
# .env 파일에 ANTHROPIC_API_KEY 추가
```

### 설정 파일 (config.yaml)

`config.yaml`에서 주요 설정을 커스터마이징할 수 있습니다:
- AI 모델 및 파라미터
- 검색 결과 수
- 블로그 길이 및 섹션 수
- 에이전트 활성화/비활성화

### 톤 학습 (선택사항)

원하는 글쓰기 스타일이 있다면 `references/reference.md`에 예시 문서를 추가하세요. 시스템이 자동으로 톤을 학습하여 적용합니다.

## 주요 라이브러리

| 라이브러리 | 용도 |
|----------|------|
| `anthropic` | Claude API 통신 (웹 검색 및 콘텐츠 생성) |
| `pydantic` | 데이터 검증 및 설정 관리 |
| `click` | CLI 인터페이스 |
| `rich` | 진행 상황 표시 및 터미널 UI |
| `aiofiles` | 비동기 파일 I/O |
| `tenacity` | 재시도 로직 (API 호출 실패 시) |
| `python-dotenv` | 환경 변수 관리 |
| `pyyaml` | YAML 설정 파일 파싱 |

