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

from src.models import DayMeal, MealCategory, MealWeek, MenuItem

# 로깅 설정
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# SSL 인증서 검증 비활성화 경고 억제
warnings.filterwarnings("ignore", category=urllib3.exceptions.InsecureRequestWarning)

BOARD_URL = "https://www.pknu.ac.kr/main/399"
BASE_URL = "https://www.pknu.ac.kr/main/399"

# 영어 요일 → 한국어 매핑
EN_TO_KR_DAY = {
    "Monday": "월요일",
    "Tuesday": "화요일",
    "Wednesday": "수요일",
    "Thursday": "목요일",
    "Friday": "금요일",
}


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

    # bdlTitle 클래스 셀 내 링크에서 ?action=view&no= 패턴 찾기
    for td in soup.find_all("td", class_="bdlTitle"):
        anchor = td.find("a", href=True)
        if not anchor:
            continue
        title = anchor.get_text(strip=True)
        href = anchor.get("href", "")
        if "식단" in title and "action=view" in href:
            # 상대 URL을 절대 URL로 변환
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


def parse_meal_data(html: str) -> List[DayMeal]:
    """상세 페이지 HTML에서 요일별 식단 데이터를 파싱한다.

    부경대 식단 테이블 구조:
    - Row 0: 구분 | Monday | Tuesday | Wednesday | Thursday | Friday | 운영정보
    - Row 1: (날짜/빈칸) | 5월18일 | 5월19일 | ...
    - Row 2+: 중식(가격) | 메뉴들 | 메뉴들 | ...
    """
    error_message = "식단 데이터를 파싱할 수 없습니다. 페이지 구조가 변경되었을 수 있습니다."
    soup = BeautifulSoup(html, "lxml")
    tables = soup.find_all("table")

    all_days = []

    for table in tables:
        table_text = table.get_text()
        # 영어 요일 헤더가 있는 테이블 찾기
        if "Monday" not in table_text:
            continue

        rows = table.find_all("tr")
        if len(rows) < 3:
            continue

        # 첫 번째 행에서 요일 열 인덱스 파악
        header_cells = rows[0].find_all(["td", "th"])
        day_col_map = {}  # col_index -> korean_day_name
        for idx, cell in enumerate(header_cells):
            cell_text = cell.get_text(strip=True)
            for en_day, kr_day in EN_TO_KR_DAY.items():
                if en_day in cell_text:
                    day_col_map[idx] = kr_day
                    break

        if len(day_col_map) < 5:
            continue

        # 두 번째 행에서 날짜 추출
        date_cells = rows[1].find_all(["td", "th"])
        day_dates = {}
        for idx, kr_day in day_col_map.items():
            if idx < len(date_cells):
                date_text = date_cells[idx].get_text(strip=True)
                # "5월 18일" 형식에서 날짜 추출
                m = re.search(r"(\d{1,2})월\s*(\d{1,2})일", date_text)
                if m:
                    day_dates[kr_day] = f"{m.group(1)}. {m.group(2)}."
                else:
                    day_dates[kr_day] = date_text

        # 세 번째 행 이후에서 메뉴 데이터 추출
        day_categories = {kr: [] for kr in EN_TO_KR_DAY.values()}

        for row in rows[2:]:
            cells = row.find_all(["td", "th"])
            if not cells:
                continue

            # 첫 셀에서 식사 구분 추출 (예: "중식(5,500원)")
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

            # 각 요일 열에서 메뉴 추출
            for col_idx, kr_day in day_col_map.items():
                if col_idx < len(cells):
                    cell = cells[col_idx]
                    menu_text = cell.get_text(separator="\n", strip=True)
                    menu_items = _parse_menu_items(menu_text)
                    if menu_items:
                        day_categories[kr_day].append(
                            MealCategory(category_name=category_name, menu_items=menu_items)
                        )

        # DayMeal 객체 생성
        days = []
        for kr_day in ["월요일", "화요일", "수요일", "목요일", "금요일"]:
            days.append(DayMeal(
                day_name=kr_day,
                date=day_dates.get(kr_day, ""),
                categories=day_categories[kr_day],
            ))

        if any(day.categories for day in days):
            all_days.extend(days)
            break  # 첫 번째 유효 테이블만 사용

    if len(all_days) == 5:
        return all_days

    raise ValueError(error_message)


def _parse_menu_items(text: str) -> List[MenuItem]:
    """셀 텍스트에서 메뉴 항목을 추출한다."""
    if not text.strip():
        return []

    items = []
    lines = re.split(r"[\n\r]+", text)

    for line in lines:
        line = line.strip()
        if not line:
            continue
        # 운영시간, 전화번호 등 제외
        if re.match(r"^(Open|Close|☎|※|\*)", line):
            continue
        if re.match(r"^[\d\s:~\-]+$", line):
            continue
        items.append(MenuItem(name=line))

    return items


def scrape() -> MealWeek:
    """전체 스크래핑 프로세스를 실행한다."""
    # 1. 게시판 목록 페이지 가져오기
    try:
        html = fetch_page(BOARD_URL)
    except (requests.ConnectionError, requests.exceptions.SSLError):
        logger.error("네트워크 연결에 실패했습니다.")
        sys.exit(1)
    except requests.HTTPError as e:
        logger.error(f"HTTP 오류: 상태 코드 {e.response.status_code}")
        sys.exit(1)

    # 2. 최신 식단 게시물 찾기
    result = find_latest_post(html)
    if result is None:
        logger.error("식단 게시물을 찾을 수 없습니다.")
        sys.exit(1)
    post_url, title = result
    logger.info(f"최신 게시물: {title}")
    logger.info(f"URL: {post_url}")

    # 3. 상세 페이지 가져오기
    try:
        detail_html = fetch_page(post_url)
    except (requests.ConnectionError, requests.exceptions.SSLError):
        logger.error("네트워크 연결에 실패했습니다.")
        sys.exit(1)
    except requests.HTTPError as e:
        logger.error(f"HTTP 오류: 상태 코드 {e.response.status_code}")
        sys.exit(1)

    # 4. 식단 데이터 파싱
    try:
        days = parse_meal_data(detail_html)
    except ValueError:
        logger.error("식단 데이터를 파싱할 수 없습니다. 페이지 구조가 변경되었을 수 있습니다.")
        sys.exit(1)

    # 5. 날짜 범위 파싱
    date_info = parse_date_range(title)
    if date_info:
        date_range_str, start_date, end_date = date_info
    else:
        date_range_str, start_date, end_date = "", "", ""

    # 6. MealWeek 객체 생성 및 반환
    return MealWeek(
        title=title,
        date_range=date_range_str,
        start_date=start_date,
        end_date=end_date,
        days=days,
    )
