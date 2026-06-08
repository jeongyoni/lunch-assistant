"""학식 페이지에서 오늘 중식 메뉴를 수집."""
import re
import logging

from .config import MENU_URL, SCRAPE_HEADERS
from .errors import ScrapeError, MenuNotFoundError
from .utils import request_with_retry, weekday_name

log = logging.getLogger(__name__)


def _split_menu(raw):
    """쉼표·줄바꿈·가운뎃점 등 다양한 구분자로 분리."""
    if not raw:
        return []
    parts = re.split(r"[,\n·ㆍ・]+", raw)
    return [p.strip() for p in parts if p.strip()]


def fetch_today_menu():
    """오늘(KST) 중식 메뉴 리스트를 반환.

    - 요청/파싱 실패 → ScrapeError (진짜 장애)
    - 메뉴 없음/표 없음 → MenuNotFoundError (휴무·미등록)
    """
    from bs4 import BeautifulSoup  # 지연 임포트

    try:
        resp = request_with_retry("GET", MENU_URL, headers=SCRAPE_HEADERS, timeout=15)
    except Exception as e:  # noqa: BLE001
        raise ScrapeError(f"학식 페이지 요청 실패: {e}") from e

    # 인코딩 보정: requests가 ISO-8859-1로 추정하면 한글이 깨짐
    if not resp.encoding or resp.encoding.lower() in ("iso-8859-1", "ascii"):
        resp.encoding = resp.apparent_encoding

    try:
        soup = BeautifulSoup(resp.text, "html.parser")
    except Exception as e:  # noqa: BLE001
        raise ScrapeError(f"HTML 파싱 실패: {e}") from e

    today = weekday_name()

    for table in soup.find_all("table"):
        text = table.get_text()
        if "중식" not in text or "월요일" not in text:
            continue

        rows = table.find_all("tr")

        # 헤더에서 '중식' 칼럼 위치 탐지 (못 찾으면 index 2 폴백)
        lunch_col = 2
        for row in rows:
            cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
            hit = next((i for i, h in enumerate(cells) if "중식" in h), None)
            if hit is not None:
                lunch_col = hit
                break

        # 오늘 요일 행 찾기
        for row in rows:
            cells = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
            if cells and cells[0] == today:
                items = _split_menu(cells[lunch_col] if len(cells) > lunch_col else "")
                if not items:
                    raise MenuNotFoundError(f"{today} 중식 메뉴가 비어 있습니다.")
                log.info("메뉴 %d개 수집: %s", len(items), items)
                return items

    raise MenuNotFoundError(f"{today} 메뉴 표를 찾지 못했습니다.")
