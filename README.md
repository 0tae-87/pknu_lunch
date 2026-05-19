# 부경대학교 학식 메뉴 (PKNU Lunch)

부경대학교 학생식당 주간 식단표를 자동으로 가져와 웹페이지로 보여주는 서비스입니다.

🔗 **바로가기**: https://0tae-87.github.io/pknu_lunch/

## 지원 식당

- **라일락** (대연캠퍼스 학생식당)
- **한미락** (용당캠퍼스 학생식당)

## 동작 방식

1. 매주 월요일 아침, GitHub Actions가 자동 실행
2. 부경대 홈페이지에서 최신 식단 데이터 스크래핑
3. 정적 HTML 페이지 생성 후 GitHub Pages로 배포

수동 개입 없이 매주 자동 갱신됩니다.

## 로컬 실행

```bash
pip install -r requirements.txt
python src/main.py
```

`docs/index.html`에 결과가 생성됩니다.

## 문제 신고 / 개선 요청

식단이 안 나오거나 개선할 점이 있으면 [Issues](https://github.com/0tae-87/pknu_lunch/issues/new)에 남겨주세요.
