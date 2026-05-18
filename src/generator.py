"""부경대 학식 메뉴 정적 HTML 생성 모듈."""

import os
from src.models import MealWeek, DayMeal, MealCategory


def get_css() -> str:
    """반응형 인라인 CSS를 반환한다."""
    return """
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                         "Helvetica Neue", Arial, sans-serif;
            background-color: #f5f5f5;
            color: #333;
            line-height: 1.6;
            padding: 16px;
        }
        .container { max-width: 900px; margin: 0 auto; }
        header {
            text-align: center; margin-bottom: 24px; padding: 20px;
            background-color: #1a73e8; color: #fff; border-radius: 12px;
        }
        header h1 { font-size: 1.4rem; margin-bottom: 8px; }
        .date-range { font-size: 1.1rem; opacity: 0.9; }
        .day-section {
            background-color: #fff; border-radius: 12px; margin-bottom: 16px;
            overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
        .day-header {
            background-color: #e8f0fe; padding: 12px 20px;
            font-size: 1.1rem; font-weight: 700; color: #1a73e8;
            border-bottom: 1px solid #d2e3fc;
        }
        .day-content { padding: 16px 20px; }
        .meal-category { margin-bottom: 16px; }
        .meal-category:last-child { margin-bottom: 0; }
        .category-name {
            font-size: 0.95rem; font-weight: 600; color: #555;
            margin-bottom: 6px; border-left: 3px solid #1a73e8; padding-left: 8px;
        }
        .menu-list {
            list-style: none; display: flex; flex-wrap: wrap;
            gap: 6px; padding-left: 12px;
        }
        .menu-item {
            background-color: #f8f9fa; padding: 4px 10px;
            border-radius: 6px; font-size: 0.9rem; color: #444;
        }
        footer { text-align: center; margin-top: 24px; padding: 12px; font-size: 0.8rem; color: #888; }
        @media (min-width: 768px) {
            body { padding: 32px; }
            header h1 { font-size: 1.6rem; }
            .date-range { font-size: 1.2rem; }
            .day-header { font-size: 1.2rem; padding: 14px 24px; }
            .day-content { padding: 20px 24px; }
            .menu-item { font-size: 0.95rem; padding: 5px 12px; }
        }
        @media (max-width: 480px) {
            header { padding: 16px; border-radius: 8px; }
            header h1 { font-size: 1.2rem; }
            .date-range { font-size: 0.95rem; }
            .day-section { border-radius: 8px; margin-bottom: 12px; }
            .day-header { padding: 10px 16px; font-size: 1rem; }
            .day-content { padding: 12px 16px; }
            .menu-list { gap: 4px; }
            .menu-item { font-size: 0.85rem; padding: 3px 8px; }
        }
    """


def render_meal_category(category: MealCategory) -> str:
    """식사 구분을 HTML 조각으로 렌더링한다."""
    menu_items_html = "\n".join(
        f'            <li class="menu-item">{item.name}</li>'
        for item in category.menu_items
    )
    return f"""        <div class="meal-category">
            <div class="category-name">{category.category_name}</div>
            <ul class="menu-list">
{menu_items_html}
            </ul>
        </div>"""


def render_day(day_meal: DayMeal) -> str:
    """하루 식단을 HTML 조각으로 렌더링한다."""
    categories_html = "\n".join(
        render_meal_category(cat) for cat in day_meal.categories
    )
    return f"""    <section class="day-section">
        <div class="day-header">{day_meal.day_name} ({day_meal.date})</div>
        <div class="day-content">
{categories_html}
        </div>
    </section>"""


def generate_html(meal_week: MealWeek) -> str:
    """MealWeek 객체를 완전한 HTML 문서로 변환한다."""
    css = get_css()
    days_html = "\n".join(render_day(day) for day in meal_week.days)
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>부경대 학식 메뉴 - {meal_week.date_range}</title>
    <style>{css}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>부경대학교 학식 메뉴</h1>
            <div class="date-range">{meal_week.date_range}</div>
        </header>
{days_html}
        <footer>
            부경대학교 학생식당 주간 식단표
        </footer>
    </div>
</body>
</html>"""


def save_html(html: str, path: str) -> None:
    """HTML을 파일로 저장한다. UTF-8 인코딩."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
