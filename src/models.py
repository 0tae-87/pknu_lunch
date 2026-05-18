from dataclasses import dataclass
from typing import List


@dataclass
class MenuItem:
    """개별 메뉴 항목"""
    name: str  # 메뉴 이름 (예: "돈까스", "된장찌개")


@dataclass
class MealCategory:
    """식사 구분 (조식/중식/석식 등)"""
    category_name: str      # 식사 구분명 (예: "중식", "석식")
    menu_items: List[MenuItem]  # 해당 구분의 메뉴 목록


@dataclass
class DayMeal:
    """하루 식단"""
    day_name: str               # 요일 (예: "월요일")
    date: str                   # 날짜 (예: "5. 18.")
    categories: List[MealCategory]  # 식사 구분 목록


@dataclass
class MealWeek:
    """주간 식단"""
    title: str              # 원본 게시물 제목
    date_range: str         # 날짜 범위 (예: "2026. 5. 18.(월) ~ 5. 22.(금)")
    start_date: str         # 시작일
    end_date: str           # 종료일
    days: List[DayMeal]     # 월~금 식단 리스트 (5개)
