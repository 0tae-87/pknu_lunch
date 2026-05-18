"""부경대 학식 메뉴 정적 HTML 생성 모듈."""

import os
from src.models import MealWeek, DayMeal, MealCategory, Restaurant


def get_css() -> str:
    """반응형 인라인 CSS를 반환한다."""
    return """
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                         "Helvetica Neue", Arial, sans-serif;
            background-color: #f5f5f5; color: #333;
            line-height: 1.6; padding: 16px;
        }
        .container { max-width: 960px; margin: 0 auto; }
        header {
            text-align: center; margin-bottom: 24px; padding: 20px;
            background-color: #1a73e8; color: #fff; border-radius: 12px;
        }
        header h1 { font-size: 1.4rem; margin-bottom: 8px; }
        .date-range { font-size: 1.1rem; opacity: 0.9; }
        .restaurant-section {
            margin-bottom: 32px;
        }
        .restaurant-title {
            font-size: 1.2rem; font-weight: 700; color: #1a73e8;
            margin-bottom: 12px; padding-bottom: 8px;
            border-bottom: 2px solid #1a73e8;
        }
        .day-section {
            background-color: #fff; border-radius: 12px; margin-bottom: 12px;
            overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
        .day-header {
            background-color: #e8f0fe; padding: 10px 20px;
            font-size: 1rem; font-weight: 700; color: #1a73e8;
            border-bottom: 1px solid #d2e3fc;
        }
        .day-content { padding: 14px 20px; }
        .meal-category { margin-bottom: 12px; }
        .meal-category:last-child { margin-bottom: 0; }
        .category-name {
            font-size: 0.9rem; font-weight: 600; color: #555;
            margin-bottom: 6px; border-left: 3px solid #1a73e8; padding-left: 8px;
        }
        .menu-list {
            list-style: none; padding-left: 12px;
        }
        .menu-item {
            padding: 2px 0; font-size: 0.9rem; color: #444;
        }
        .fixed-menu-section {
            background-color: #fff; border-radius: 12px;
            padding: 16px 20px; margin-bottom: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
        .fixed-cat-name {
            font-size: 0.95rem; font-weight: 600; color: #333;
            margin-bottom: 4px;
        }
        .fixed-items {
            font-size: 0.85rem; color: #555; margin-bottom: 10px;
            line-height: 1.5;
        }
        footer {
            text-align: center; margin-top: 24px; padding: 12px;
            font-size: 0.8rem; color: #888;
        }
        @media (min-width: 768px) {
            body { padding: 32px; }
            header h1 { font-size: 1.6rem; }
            .restaurant-title { font-size: 1.3rem; }
        }
        @media (max-width: 480px) {
            header { padding: 16px; border-radius: 8px; }
            header h1 { font-size: 1.2rem; }
            .day-section { border-radius: 8px; margin-bottom: 10px; }
            .day-header { padding: 8px 14px; font-size: 0.95rem; }
            .day-content { padding: 10px 14px; }
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
    date_str = f" ({day_meal.date})" if day_meal.date else ""
    return f"""    <section class="day-section">
        <div class="day-header">{day_meal.day_name}{date_str}</div>
        <div class="day-content">
{categories_html}
        </div>
    </section>"""


def render_restaurant(restaurant: Restaurant) -> str:
    """식당 섹션을 HTML로 렌더링한다."""
    parts = []
    title = restaurant.name or "식당"
    parts.append(f'    <div class="restaurant-section">')
    parts.append(f'        <h2 class="restaurant-title">{title}</h2>')

    # 주간 메뉴
    if restaurant.days:
        for day in restaurant.days:
            if day.categories:
                parts.append(render_day(day))

    # 상시 메뉴
    if restaurant.fixed_menu:
        parts.append('        <div class="fixed-menu-section">')
        for cat in restaurant.fixed_menu:
            items_str = " / ".join(item.name for item in cat.menu_items)
            parts.append(f'            <div class="fixed-cat-name">{cat.category_name}</div>')
            parts.append(f'            <div class="fixed-items">{items_str}</div>')
        parts.append('        </div>')

    parts.append('    </div>')
    return "\n".join(parts)


def generate_html(meal_week: MealWeek) -> str:
    """MealWeek 객체를 완전한 HTML 문서로 변환한다."""
    css = get_css()

    if meal_week.restaurants:
        body_html = "\n".join(render_restaurant(r) for r in meal_week.restaurants)
    else:
        body_html = "\n".join(render_day(day) for day in meal_week.days)

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
{body_html}
        <footer>
            부경대학교 학생식당 주간 식단표 | 매주 월요일 자동 업데이트
        </footer>
    </div>
</body>
</html>"""


def save_html(html: str, path: str) -> None:
    """HTML을 파일로 저장한다. UTF-8 인코딩."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
