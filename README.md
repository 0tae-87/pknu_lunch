# 부경대학교 학식 메뉴 스크래퍼 (PKNU Meal Scraper)

부경대학교 홈페이지의 학식 게시판에서 주간 식단표를 자동으로 스크래핑하여 정적 HTML 페이지를 생성하고, GitHub Pages를 통해 배포하는 자동화 시스템입니다.

## 기능

- 부경대학교 학식 게시판(https://www.pknu.ac.kr/main/399)에서 최신 주간 식단표 자동 스크래핑
- 반응형 정적 HTML 페이지 자동 생성
- GitHub Actions를 통한 매주 자동 갱신
- GitHub Pages를 통한 무료 배포

## 프로젝트 구조

```
├── .github/workflows/   # GitHub Actions 워크플로우
├── src/                 # 소스 코드 (scraper, generator)
├── docs/                # GitHub Pages 배포 디렉토리
├── tests/               # 테스트 코드
├── requirements.txt     # Python 의존성
└── README.md
```

## 설치 및 실행

```bash
pip install -r requirements.txt
python src/main.py
```

## 기술 스택

- Python 3.x
- requests + BeautifulSoup4 (웹 스크래핑)
- GitHub Actions (자동화)
- GitHub Pages (배포)

## 라이선스

MIT
