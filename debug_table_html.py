from src.scraper import fetch_page
from bs4 import BeautifulSoup

html = fetch_page("https://www.pknu.ac.kr/main/399?action=view&no=724826")
soup = BeautifulSoup(html, "lxml")
tables = soup.find_all("table")

# table 2 HTML structure
t = tables[2]
rows = t.find_all("tr")
for i, row in enumerate(rows):
    cells = row.find_all(["td", "th"])
    print(f"Row {i}: {len(cells)} cells")
    for j, cell in enumerate(cells):
        print(f"  Cell {j}: {cell.get_text(separator='|', strip=True)[:80]}")
