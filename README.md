# Blog Agents - 멀티 에이전트 블로그 콘텐츠 생성 시스템

키워드로부터 자동으로 고품질 블로그 콘텐츠를 생성하는 Python 기반 AI Agent 시스템입니다. 3개의 전문화된 에이전트가 협력하여 작동합니다.

## 주요 기능

- **멀티 에이전트 아키텍처**: 3개의 전문화된 에이전트가 협력
  - **PostSearcher**: 웹에서 관련 게시글을 검색하고 순위 매김
  - **BlogPlanner**: 게시글을 분석하고 구조화된 개요 작성
  - **BlogWriter**: 커스터마이징 가능한 톤으로 블로그 포스트 생성

- **톤 학습**: 참조 문서에서 글쓰기 스타일을 학습하고 일관되게 적용

- **웹 검색 통합**: Google Custom Search와 Bing Web Search API 모두 지원

- **체크포인트 시스템**: 중단된 작업을 재개할 수 있음

- **Rich CLI 인터페이스**: 진행 상황 표시가 있는 사용자 친화적 명령줄 인터페이스

## 아키텍처

```
┌─────────────────────────────────────────────────────┐
│                  Orchestrator                        │
│            (워크플로우 조정)                          │
└──────────────┬──────────────┬──────────────┬────────┘
               │              │              │
       ┌───────▼──────┐ ┌─────▼──────┐ ┌────▼─────────┐
       │ PostSearcher │ │ BlogPlanner│ │ BlogWriter   │
       │              │ │            │ │              │
       │ • 웹 검색    │ │ • 분석     │ │ • 작성       │
       │ • 추출       │ │ • 개요     │ │ • 톤 적용    │
       │ • 순위 매김  │ │ • 계획     │ │ • 다듬기     │
       └──────────────┘ └────────────┘ └──────────────┘
                                              │
                                       ┌──────▼─────────┐
                                       │  ToneLearner   │
                                       │    (스킬)      │
                                       └────────────────┘
```

## 설치 방법

### 사전 요구사항

- Python 3.9 이상
- API 키:
  - Anthropic API 키 (필수)
  - Google Custom Search API 키 + Search Engine ID (선택)
  - Bing Web Search API 키 (선택)

### 설정

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
# .env 파일을 편집하여 API 키 추가
```

5. 시스템 설정 (선택):
```bash
# config.yaml을 편집하여 에이전트 동작 커스터마이징
```

## 빠른 시작

### 블로그 포스트 생성

```bash
python -m blog_agents.cli.blog_cli generate --keywords "Python asyncio 모범 사례"
```

실행 과정:
1. 관련 게시글 검색
2. 분석 및 개요 작성
3. 블로그 포스트 작성
4. `outputs/` 디렉토리에 저장

### 글쓰기 톤 분석

```bash
python -m blog_agents.cli.blog_cli analyze-tone --file references/reference.md
```

### 검색만 실행

```bash
python -m blog_agents.cli.blog_cli search-only --keywords "머신러닝"
```

## 설정

### 환경 변수 (.env)

```env
ANTHROPIC_API_KEY=your_api_key_here
GOOGLE_SEARCH_API_KEY=your_google_key
GOOGLE_SEARCH_ENGINE_ID=your_search_engine_id
```

### 시스템 설정 (config.yaml)

```yaml
ai:
  model: "claude-sonnet-4-5-20250929"
  temperature: 0.7

search:
  provider: "google"  # 또는 "bing"
  max_results: 10

blog_agents:
  max_search_results: 3
  target_blog_length: 1500
  reference_file: "references/reference.md"
```

## 사용 예시

### Python API

```python
import asyncio
from blog_agents.core.orchestrator import BlogOrchestrator

async def generate_blog():
    orchestrator = BlogOrchestrator()
    result = await orchestrator.generate_blog("Python 테스팅")
    print(f"블로그 저장 위치: {result['blog_file']}")

asyncio.run(generate_blog())
```

### CLI 명령어

```bash
# 상세 출력과 함께 전체 생성
python -m blog_agents.cli.blog_cli generate -k "Docker 모범 사례" -v

# 모든 워크플로우 목록 표시
python -m blog_agents.cli.blog_cli list-workflows

# 버전 표시
python -m blog_agents.cli.blog_cli version
```

## 프로젝트 구조

```
news-crawler/
├── blog_agents/
│   ├── agents/          # 3개의 전문화된 에이전트
│   ├── config/          # 설정 관리
│   ├── core/            # Orchestrator 및 base agent
│   ├── search/          # 검색 제공자 통합
│   ├── skills/          # ToneLearner 스킬
│   ├── utils/           # 유틸리티 (retry, 파일 I/O, validators)
│   └── cli/             # 명령줄 인터페이스
├── outputs/             # 생성된 블로그 및 체크포인트
├── references/          # 톤 학습을 위한 참조 문서
├── examples/            # 사용 예시
├── config.yaml          # 메인 설정 파일
└── blog_agents_requirements.txt
```

## 워크플로우

1. **PostSearcher Agent**:
   - Google/Bing API를 사용하여 웹 검색 실행
   - 상위 결과에서 콘텐츠 추출
   - Claude를 사용하여 게시글 관련성 순위 매김
   - 상위 2-3개 게시글 선택
   - `outputs/search_results.json`에 저장

2. **BlogPlanner Agent**:
   - 선택된 게시글 분석
   - 주제, 갭, 핵심 개념 식별
   - 구조화된 개요 생성 (3-7개 섹션)
   - 게시글에서 핵심 포인트 추출
   - `outputs/blog_plan.json`에 저장

3. **BlogWriter Agent**:
   - 참조 문서에서 톤 프로필 로드
   - 흥미로운 훅으로 서론 작성
   - 개요를 기반으로 각 섹션 작성
   - 행동 유도 문구가 있는 결론 작성
   - 톤 일관성을 위해 검토 및 다듬기
   - `outputs/{제목}-{날짜}.md`에 저장

## 참조 문서

원하는 글쓰기 스타일의 예시를 포함한 `references/reference.md`를 생성하세요. ToneLearner는 다음을 분석합니다:
- 톤 및 보이스 특성
- 어휘 및 언어 수준
- 문장 패턴 및 구조
- 서식 선호도

## 고급 기능

### 체크포인트 시스템

워크플로우가 중단된 경우 재개할 수 있습니다:

```python
orchestrator = BlogOrchestrator()
result = await orchestrator.generate_blog(
    keywords="주제",
    resume_from="workflow-id"
)
```

### 커스텀 톤 적용

```python
from blog_agents.skills.tone_learner import ToneLearner

tone_learner = ToneLearner(config)
profile = tone_learner.analyze_tone("my_style.md")
adjusted = tone_learner.apply_tone(content, profile)
score = tone_learner.validate_tone_match(adjusted)
```

### 단계별 실행

```python
orchestrator = BlogOrchestrator()

# 각 단계를 개별적으로 실행
search_result = await orchestrator.search_only("키워드")
plan_result = await orchestrator.plan_only()
write_result = await orchestrator.write_only()
```

## 로깅

로그는 다음 위치에 기록됩니다:
- 콘솔 출력 (INFO 레벨)
- `blog_agents.log` 파일 (--verbose 사용 시 DEBUG 레벨)

## 문제 해결

### API 키 오류
- `.env` 파일이 존재하고 유효한 API 키가 포함되어 있는지 확인
- 환경 변수가 로드되는지 확인

### 검색 오류
- Google Custom Search Engine이 구성되어 있는지 확인
- API 할당량 및 속도 제한 확인

### 톤 분석 실패
- `references/reference.md`가 존재하는지 확인
- 파일에 충분한 콘텐츠가 포함되어 있는지 확인 (최소 500단어 권장)

## 기여하기

사용 패턴은 `examples/blog_generation_example.py`를 참조하세요.

## 라이센스

MIT License

## 지원

문제 및 질문이 있는 경우 GitHub에서 이슈를 열어주세요.
