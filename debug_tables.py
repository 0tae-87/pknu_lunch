from src.scraper import fetch_page
from bs4 import BeautifulSoup

html = fetch_page("https://www.pknu.ac.kr/main/399?action=view&no=724826")
soup = BeautifulSoup(html, "lxml")
tables = soup.find_all("table")

for i, t in enumerate(tables):
    rows = t.find_all("tr")
    print(f"--- table {i} (rows:{len(rows)}) ---")
    print(t.get_text()[:400])
    print()
