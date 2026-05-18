"""부경대학교 학식 메뉴 스크래퍼 모듈."""

import logging
import re
import ssl
import sys
import warnings
from typing import List, Optional, Tuple
from urllib.parse import urljoin

import requests
import urllib3
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

from src.models import DayMeal, MealCategory, MealWeek, MenuItem, Restaurant

# 로깅 설정
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# SSL 인증서 검증 비활성화 경고 억제
warnings.filterwarnings("ignore", category=urllib3.exceptions.InsecureRequestWarning)

BOARD_URL = "https://www.pknu.ac.kr/main/399"
BASE_URL = "https://www.pknu.ac.kr/main/399"

EN_TO_KR_DAY = {
    "Monday": "월요일",
    "Tuesday": "화요일",
    "Wednesday": "수요일",
    "Thursday": "목요일",
    "Friday": "금요일",
}

DAY_ORDER = ["월요일", "화요일", "수요일", "목요일", "금요일"]


class SSLAdapter(HTTPAdapter):
    """TLS 호환성을 위한 커스텀 SSL 어댑터."""

    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ctx.set_ciphers("DEFAULT:@SECLEVEL=1")
        kwargs["ssl_context"] = ctx
        return super().init_poolmanager(*args, **kwargs)


def fetch_page(url: str) -> str:
    """URL에서 HTML 페이지를 가져온다."""
    session = requests.Session()
    session.mount("https://", SSLAdapter())
    response = session.get(url, verify=False)
    response.raise_for_status()
    return response.text


def find_latest_post(html: str) -> Optional[Tuple[str, str]]:
    """게시판 목록에서 가장 최근 식단 게시물의 상세 URL과 제목을 찾는다."""
    soup = BeautifulSoup(html, "lxml")

    for td in soup.find_all("td", class_="bdlTitle"):
        anchor = td.find("a", href=True)
        if not anchor:
            continue
        title = anchor.get_text(strip=True)
        href = anchor.get("href", "")
        if "식단" in title and "action=view" in href:
            url = urljoin(BASE_URL, href)
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


def parse_all_restaurants(html: str) -> List[Restaurant]:
    """상세 페이지에서 대연캠/용당캠 학생식당 데이터만 파싱한다."""
    soup = BeautifulSoup(html, "lxml")
    tables = soup.find_all("table")
    restaurants = []

    # 영어 요일 헤더가 있는 테이블만 수집 (주간 메뉴 식당)
    weekly_tables = []
    for table in tables:
        if "Monday" in table.get_text():
            weekly_tables.append(table)

    # 첫 번째 = 라일락(대연캠), 두 번째 = 한미락(용당캠)
    names = ["라일락 (대연캠퍼스)", "한미락 (용당캠퍼스)"]
    for i, table in enumerate(weekly_tables):
        name = names[i] if i < len(names) else f"식당 {i+1}"
        restaurant = _parse_weekly_table(table, soup)
        if restaurant:
            restaurant.name = name
            restaurants.append(restaurant)

    return restaurants


def _find_table_title(table, soup) -> str:
    """테이블 앞에서 식당 이름을 찾는다."""
    # 테이블 앞의 형제 요소에서 제목 찾기
    prev = table.find_previous(["h2", "h3", "h4", "p", "strong", "span"])
    if prev:
        text = prev.get_text(strip=True)
        # "캠퍼스" 또는 "식당" 이 포함된 텍스트를 제목으로 사용
        if text and len(text) < 50:
            return text
    return ""


def _parse_weekly_table(table, soup) -> Optional[Restaurant]:
    """요일별 메뉴 테이블을 파싱한다."""
    rows = table.find_all("tr")
    if len(rows) < 3:
        return None

    # 헤더 행에서 요일 열 인덱스
    header_cells = rows[0].find_all(["td", "th"])
    day_col_map = {}
    for idx, cell in enumerate(header_cells):
        cell_text = cell.get_text(strip=True)
        for en_day, kr_day in EN_TO_KR_DAY.items():
            if en_day in cell_text:
                day_col_map[idx] = kr_day
                break

    if len(day_col_map) < 5:
        return None

    # 날짜 행 (두 번째 행)
    date_cells = rows[1].find_all(["td", "th"])
    day_dates = {}
    for idx, kr_day in day_col_map.items():
        if idx < len(date_cells):
            date_text = date_cells[idx].get_text(strip=True)
            m = re.search(r"(\d{1,2})월\s*(\d{1,2})일", date_text)
            if m:
                day_dates[kr_day] = f"{m.group(1)}. {m.group(2)}."
            else:
                day_dates[kr_day] = ""

    # 메뉴 행들
    day_categories = {kr: [] for kr in DAY_ORDER}

    for row in rows[2:]:
        cells = row.find_all(["td", "th"])
        if not cells:
            continue

        first_text = cells[0].get_text(strip=True)
        category_name = None
        if "조식" in first_text:
            category_name = "조식"
        elif "중식" in first_text:
            category_name = "중식"
        elif "석식" in first_text:
            category_name = "석식"

        if category_name is None:
            continue

        # 가격 정보 추출
        price_info = ""
        price_match = re.search(r"\(([^)]*원[^)]*)\)", first_text)
        if price_match:
            price_info = price_match.group(1)

        for col_idx, kr_day in day_col_map.items():
            if col_idx < len(cells):
                cell = cells[col_idx]
                menu_text = cell.get_text(separator="\n", strip=True)
                menu_items = _parse_menu_items(menu_text)
                if menu_items:
                    cat_name = category_name
                    if price_info:
                        cat_name = f"{category_name} ({price_info})"
                    day_categories[kr_day].append(
                        MealCategory(category_name=cat_name, menu_items=menu_items)
                    )

    # DayMeal 생성
    days = []
    for kr_day in DAY_ORDER:
        days.append(DayMeal(
            day_name=kr_day,
            date=day_dates.get(kr_day, ""),
            categories=day_categories[kr_day],
        ))

    if not any(day.categories for day in days):
        return None

    name = _find_table_title(table, soup)
    return Restaurant(name=name, days=days)


def _parse_fixed_menu_table(table, soup) -> Optional[Restaurant]:
    """상시 메뉴 테이블을 파싱한다 (한식, 분식, 파스타 등)."""
    rows = table.find_all("tr")
    if len(rows) < 2:
        return None

    # Monday가 있으면 주간 메뉴 → 이미 처리됨
    if "Monday" in table.get_text():
        return None

    categories = []
    for row in rows:
        cells = row.find_all(["td", "th"])
        if len(cells) < 2:
            continue

        cat_name = cells[0].get_text(strip=True)
        if not cat_name or cat_name == "구분":
            continue

        # "메뉴" 열 또는 전체 행의 나머지 셀에서 메뉴 추출
        menu_text = ""
        for cell in cells[1:]:
            cell_text = cell.get_text(strip=True)
            # "운영정보" 열은 건너뜀
            if "Open" in cell_text or "☎" in cell_text:
                continue
            if cell_text:
                menu_text += cell_text + "\n"

        if menu_text.strip():
            items = []
            # 상시 메뉴는 "·" 또는 ","로 구분
            parts = re.split(r"[·,]", menu_text)
            for part in parts:
                part = part.strip()
                if part and len(part) > 1:
                    # 운영시간/전화번호 제외
                    if re.match(r"^(Open|Close|☎|※)", part):
                        continue
                    items.append(MenuItem(name=part))

            if items:
                categories.append(MealCategory(category_name=cat_name, menu_items=items))

    if not categories:
        return None

    name = _find_table_title(table, soup)
    return Restaurant(name=name, fixed_menu=categories)


def _parse_menu_items(text: str) -> List[MenuItem]:
    """셀 텍스트에서 메뉴 항목을 추출한다.

    원본 사이트에서 줄바꿈(\n)은 실제 메뉴 구분이 아닌 경우가 있다.
    단독 "/" 나 "&" 줄은 앞뒤 항목을 합친다.
    """
    if not text.strip():
        return []

    lines = re.split(r"[\n\r]+", text)
    # 먼저 단독 "/" 나 "&"를 앞뒤 줄과 합치기
    merged = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line in ("/", "&") and merged:
            # 다음 줄과 합치기
            if i + 1 < len(lines):
                merged[-1] = merged[-1] + line + lines[i + 1].strip()
                i += 2
                continue
        merged.append(line)
        i += 1

    items = []
    for line in merged:
        line = line.strip()
        if not line:
            continue
        # 운영시간, 전화번호, 주석 등 제외
        if re.match(r"^(Open|Close|☎|※|\*|\d{1,2}:\d{2})", line):
            continue
        if re.match(r"^[\d\s:~\-]+$", line):
            continue
        items.append(MenuItem(name=line))

    return items


def scrape() -> MealWeek:
    """전체 스크래핑 프로세스를 실행한다."""
    try:
        html = fetch_page(BOARD_URL)
    except (requests.ConnectionError, requests.exceptions.SSLError):
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
    logger.info(f"최신 게시물: {title}")

    try:
        detail_html = fetch_page(post_url)
    except (requests.ConnectionError, requests.exceptions.SSLError):
        logger.error("네트워크 연결에 실패했습니다.")
        sys.exit(1)
    except requests.HTTPError as e:
        logger.error(f"HTTP 오류: 상태 코드 {e.response.status_code}")
        sys.exit(1)

    restaurants = parse_all_restaurants(detail_html)
    if not restaurants:
        logger.error("식단 데이터를 파싱할 수 없습니다. 페이지 구조가 변경되었을 수 있습니다.")
        sys.exit(1)

    logger.info(f"파싱된 식당 수: {len(restaurants)}")

    date_info = parse_date_range(title)
    if date_info:
        date_range_str, start_date, end_date = date_info
    else:
        date_range_str, start_date, end_date = "", "", ""

    # 첫 번째 주간 메뉴 식당의 days를 호환용으로 설정
    first_days = []
    for r in restaurants:
        if r.days:
            first_days = r.days
            break

    return MealWeek(
        title=title,
        date_range=date_range_str,
        start_date=start_date,
        end_date=end_date,
        restaurants=restaurants,
        days=first_days,
    )
