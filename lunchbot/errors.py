"""단계별 예외. stage 값이 관리자 에러 카드에 그대로 노출됨."""


class LunchBotError(Exception):
    stage = "unknown"


class ScrapeError(LunchBotError):
    """페이지 요청/파싱 자체가 실패 (네트워크, 구조 변경 등) — 진짜 장애."""
    stage = "scrape"


class MenuNotFoundError(LunchBotError):
    """페이지는 정상이나 오늘 메뉴가 없음 — 장애 아님(휴무/미등록)."""
    stage = "menu-empty"


class OpenAIError(LunchBotError):
    """OpenAI 호출 실패 — 메뉴 전송은 계속하고 해당 부분만 생략."""
    stage = "openai"


class TeamsError(LunchBotError):
    """Teams 전송 실패 — 치명적."""
    stage = "teams"
