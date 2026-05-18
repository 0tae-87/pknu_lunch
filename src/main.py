"""부경대 학식 스크래퍼 메인 실행 스크립트."""

import os
import sys

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.scraper import scrape
from src.generator import generate_html, save_html


def main():
    """메인 실행 함수: 스크래핑 → HTML 생성 → 파일 저장."""
    # 1. 식단 데이터 스크래핑
    meal_week = scrape()

    # 2. HTML 생성
    html = generate_html(meal_week)

    # 3. 파일 저장 (docs/index.html)
    output_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "docs",
        "index.html",
    )
    save_html(html, output_path)
    print(f"식단 페이지가 생성되었습니다: {output_path}")


if __name__ == "__main__":
    main()
