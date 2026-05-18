"""부경대학교 학식 메뉴 스크래퍼 모듈."""

import logging
import re
import sys
import warnings
from typing import List, Optional, Tuple
from urllib.parse import urljoin

import requests
import urllib3
from bs4 import BeautifulSoup

from src.models import DayMeal, MealCategory, MealWeek, MenuItem

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# SSL 인증서 검증 비활성화 경고 억제
warnings.filterwarnings("ignore", category=urllib3.exceptions.InsecureRequestWarning)

BOARD_URL = "https://www.pknu.ac.kr/main/399"


def fetch_page(url: str) -> str:
    """URL에서 HTML 페이지를 가져온다."""
    response = requests.get(url, verify=False)
    response.raise_for_status()
    return response.text


def find_latest_post(html: str) -> Optional[Tuple[str, str]]:
    """게시판 목록 HTML에서 가장 최근 식단 게시물을 찾는다."""
    soup = BeautifulSoup(html, "lxml")
    base_url = "https://www.pknu.ac.kr"

    for anchor in soup.find_all("a"):
        title = anchor.get("title") or anchor.get_text(strip=True)
        if not title:
            continue
        if "식단" in title:
            href = anchor.get("href")
            if not href:
                continue
            url = urljoin(base_url, href)
            return (url, title)

    return None


def parse_date_range(title: str) -> Optional[Tuple[str, str, str]]:
    """게시물 제목에서 날짜 범위를 추출한다."""
    pattern = (
        r"(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.\s*\([^)]+\)"
        r"\s*~\s*"
        r"(\d{1,2})\.\s*(\d{1,2})\.\s*\([^)]+\)"
    )
    match = re.search(pattern, title)
    if not match:
        return None

    date_range_str = match.group(0)
    year = match.group(1)
    start_month = match.group(2)
    start_day = match.group(3)
    end_month = match.group(4)
    end_day = match.group(5)

    start_date = f"{year}. {start_month}. {start_day}."
    end_date = f"{year}. {end_month}. {end_day}."
    return (date_range_str, start_date, end_date)


WEEKDAY_NAMES = ["월요일", "화요일", "수요일", "목요일", "금요일"]
MEAL_CATEGORY_NAMES = ["조식", "중식", "석식"]


def parse_meal_data(html: str) -> List[DayMeal]:
    """상세 페이지 HTML에서 요일별 식단 데이터를 파싱한다."""
    error_message = "식단 데이터를 파싱할 수 없습니다. 페이지 구조가 변경되었을 수 있습니다."
    soup = BeautifulSoup(html, "lxml")

    days = _parse_table_layout(soup)
    if days and len(days) == 5:
        return days

    days = _parse_div_layout(soup)
    if days and len(days) == 5:
        return days

    days = _parse_text_layout(soup)
    if days and len(days) == 5:
        return days

    raise ValueError(error_message)


def _parse_table_layout(soup: BeautifulSoup) -> Optional[List[DayMeal]]:
    """테이블 기반 레이아웃에서 식단 데이터를 파싱한다."""
    tables = soup.find_all("table")
    for table in tables:
        table_text = table.get_text()
        weekday_count = sum(1 for day in WEEKDAY_NAMES if day in table_text)
        if weekday_count < 3:
            continue
        days = _parse_table_row_per_day(table)
        if days and len(days) == 5:
            return days
        days = _parse_table_col_per_day(table)
        if days and len(days) == 5:
            return days
    return None


def _parse_table_row_per_day(table) -> Optional[List[DayMeal]]:
    """행 기반 테이블 파싱."""
    rows = table.find_all("tr")
    days = []
    for row in rows:
        cells = row.find_all(["td", "th"])
        if not cells:
            continue
        row_text = cells[0].get_text(strip=True)
        matched_day = None
        for day_name in WEEKDAY_NAMES:
            if day_name in row_text:
                matched_day = day_name
                break
        if matched_day is None:
            continue
        categories = _extract_categories_from_cells(cells[1:])
        if not categories:
            categories = _extract_categories_from_text(
                " ".join(cell.get_text(separator="\n") for cell in cells[1:])
            )
        date = _extract_date_from_text(row_text)
        days.append(DayMeal(day_name=matched_day, date=date, categories=categories if categories else []))
    return days if len(days) == 5 else None


def _parse_table_col_per_day(table) -> Optional[List[DayMeal]]:
    """열 기반 테이블 파싱."""
    rows = table.find_all("tr")
    if len(rows) < 2:
        return None
    header_cells = rows[0].find_all(["td", "th"])
    day_col_indices = {}
    for idx, cell in enumerate(header_cells):
        cell_text = cell.get_text(strip=True)
        for day_name in WEEKDAY_NAMES:
            if day_name in cell_text:
                day_col_indices[day_name] = idx
                break
    if len(day_col_indices) < 5:
        return None
    day_categories = {day: [] for day in WEEKDAY_NAMES}
    for row in rows[1:]:
        cells = row.find_all(["td", "th"])
        if not cells:
            continue
        first_cell_text = cells[0].get_text(strip=True)
        category_name = None
        for cat in MEAL_CATEGORY_NAMES:
            if cat in first_cell_text:
                category_name = cat
                break
        if category_name is None:
            continue
        for day_name, col_idx in day_col_indices.items():
            if col_idx < len(cells):
                cell = cells[col_idx]
                menu_items = _extract_menu_items_from_cell(cell)
                if menu_items:
                    day_categories[day_name].append(
                        MealCategory(category_name=category_name, menu_items=menu_items)
                    )
    days = []
    for day_name in WEEKDAY_NAMES:
        days.append(DayMeal(day_name=day_name, date="", categories=day_categories[day_name]))
    if any(day.categories for day in days):
        return days
    return None


def _parse_div_layout(soup: BeautifulSoup) -> Optional[List[DayMeal]]:
    """div 기반 레이아웃 파싱."""
    body_text = soup.get_text()
    weekday_count = sum(1 for day in WEEKDAY_NAMES if day in body_text)
    if weekday_count < 5:
        return None
    days = []
    content_area = soup.find("div", class_=re.compile(r"(content|body|view|article)", re.I))
    if content_area is None:
        content_area = soup.body if soup.body else soup
    for day_name in WEEKDAY_NAMES:
        day_element = content_area.find(string=re.compile(re.escape(day_name)))
        if day_element is None:
            continue
        parent = day_element.parent
        if parent is None:
            continue
        categories = _extract_categories_from_siblings(parent)
        date = _extract_date_from_text(str(day_element))
        days.append(DayMeal(day_name=day_name, date=date, categories=categories if categories else []))
    return days if len(days) == 5 else None


def _parse_text_layout(soup: BeautifulSoup) -> Optional[List[DayMeal]]:
    """텍스트 기반 파싱."""
    content_area = soup.find("div", class_=re.compile(r"(content|body|view|article)", re.I))
    if content_area is None:
        content_area = soup.body if soup.body else soup
    full_text = content_area.get_text(separator="\n")
    weekday_count = sum(1 for day in WEEKDAY_NAMES if day in full_text)
    if weekday_count < 5:
        return None
    days = []
    for i, day_name in enumerate(WEEKDAY_NAMES):
        start_idx = full_text.find(day_name)
        if start_idx == -1:
            return None
        if i < len(WEEKDAY_NAMES) - 1:
            next_day = WEEKDAY_NAMES[i + 1]
            end_idx = full_text.find(next_day, start_idx + len(day_name))
            day_text = full_text[start_idx:end_idx] if end_idx != -1 else full_text[start_idx:]
        else:
            day_text = full_text[start_idx:]
        categories = _extract_categories_from_text(day_text)
        date = _extract_date_from_text(day_text)
        days.append(DayMeal(day_name=day_name, date=date, categories=categories if categories else []))
    return days if len(days) == 5 else None


def _extract_categories_from_cells(cells) -> List[MealCategory]:
    """셀 목록에서 식사 구분과 메뉴를 추출한다."""
    categories = []
    for cell in cells:
        cell_text = cell.get_text(separator="\n", strip=True)
        if not cell_text:
            continue
        category_name = None
        for cat in MEAL_CATEGORY_NAMES:
            if cat in cell_text:
                category_name = cat
                break
        if category_name:
            menu_items = _extract_menu_items_from_cell(cell)
            if menu_items:
                categories.append(MealCategory(category_name=category_name, menu_items=menu_items))
    return categories


def _extract_categories_from_text(text: str) -> List[MealCategory]:
    """텍스트에서 식사 구분과 메뉴를 추출한다."""
    categories = []
    for cat_name in MEAL_CATEGORY_NAMES:
        cat_idx = text.find(cat_name)
        if cat_idx == -1:
            continue
        end_idx = len(text)
        for next_cat in MEAL_CATEGORY_NAMES:
            if next_cat == cat_name:
                continue
            next_idx = text.find(next_cat, cat_idx + len(cat_name))
            if next_idx != -1 and next_idx < end_idx:
                end_idx = next_idx
        section_text = text[cat_idx + len(cat_name):end_idx]
        menu_items = _extract_menu_items_from_text(section_text)
        if menu_items:
            categories.append(MealCategory(category_name=cat_name, menu_items=menu_items))
    return categories


def _extract_categories_from_siblings(element) -> List[MealCategory]:
    """요소의 형제 요소들에서 식사 구분을 추출한다."""
    text_parts = []
    current = element.next_sibling
    count = 0
    while current and count < 50:
        if hasattr(current, 'get_text'):
            t = current.get_text(strip=True)
            if any(day in t for day in WEEKDAY_NAMES):
                break
            text_parts.append(t)
        elif isinstance(current, str):
            current_str = current.strip()
            if current_str:
                text_parts.append(current_str)
        current = current.next_sibling
        count += 1
    return _extract_categories_from_text("\n".join(text_parts))


def _extract_menu_items_from_cell(cell) -> List[MenuItem]:
    """셀 요소에서 메뉴 항목을 추출한다."""
    text = cell.get_text(separator="\n", strip=True)
    return _extract_menu_items_from_text(text)


def _extract_menu_items_from_text(text: str) -> List[MenuItem]:
    """텍스트에서 메뉴 항목을 추출한다."""
    if not text.strip():
        return []
    exclude_terms = set(WEEKDAY_NAMES + MEAL_CATEGORY_NAMES)
    lines = re.split(r"[\n\r]+", text)
    items = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        parts = re.split(r"[,/]", line)
        for part in parts:
            part = part.strip()
            if (not part or part in exclude_terms or
                    re.match(r"^[\d\s.()]+$", part) or len(part) < 1):
                continue
            if ":" in part:
                after_colon = part.split(":", 1)[1].strip()
                if after_colon and after_colon not in exclude_terms:
                    items.append(MenuItem(name=after_colon))
            else:
                items.append(MenuItem(name=part))
    return items


def _extract_date_from_text(text: str) -> str:
    """텍스트에서 날짜를 추출한다."""
    match = re.search(r"(\d{1,2})\.\s*(\d{1,2})\.", text)
    if match:
        return f"{match.group(1)}. {match.group(2)}."
    return ""


def scrape() -> MealWeek:
    """전체 스크래핑 프로세스를 실행한다."""
    try:
        html = fetch_page(BOARD_URL)
    except requests.ConnectionError:
        logger.error("네트워크 연결에 실패했습니다.")
        sys.exit(1)
    except requests.HTTPError as e:
        logger.error(f"HTTP 오류: 상태 코드 {e.response.status_code}")
        sys.exit(1)

    result = find_latest_post(html)
    if result is None:
        logger.error("식단 게시물을 찾을 수 없습니다.")
        sys.exit(1)
    post_url, title = result

    try:
        detail_html = fetch_page(post_url)
    except requests.ConnectionError:
        logger.error("네트워크 연결에 실패했습니다.")
        sys.exit(1)
    except requests.HTTPError as e:
        logger.error(f"HTTP 오류: 상태 코드 {e.response.status_code}")
        sys.exit(1)

    try:
        days = parse_meal_data(detail_html)
    except ValueError:
        logger.error("식단 데이터를 파싱할 수 없습니다. 페이지 구조가 변경되었을 수 있습니다.")
        sys.exit(1)

    date_info = parse_date_range(title)
    if date_info:
        date_range_str, start_date, end_date = date_info
    else:
        date_range_str, start_date, end_date = "", "", ""

    return MealWeek(
        title=title,
        date_range=date_range_str,
        start_date=start_date,
        end_date=end_date,
        days=days,
    )
