"""Teams webhook 전송과 관리자 에러 알림."""
import logging

from .config import TEAMS_WEBHOOK_URL, ADMIN_WEBHOOK_URL
from .errors import TeamsError
from .cards import build_error_card
from .utils import now_kst

log = logging.getLogger(__name__)


def _post(url, card):
    import requests  # 지연 임포트
    r = requests.post(url, json=card, timeout=15)
    log.info("Teams 응답: %s %s", r.status_code, r.text[:150])
    if r.status_code >= 400:
        raise TeamsError(f"Teams 전송 실패: HTTP {r.status_code} {r.text[:150]}")
    return r


def send_card(card):
    if not TEAMS_WEBHOOK_URL:
        raise TeamsError("TEAMS_WEBHOOK_URL 미설정")
    return _post(TEAMS_WEBHOOK_URL, card)


def send_admin_error(stage, message):
    """관리자 채널로 에러 알림. 알림 자체 실패는 로그만 남기고 삼킨다."""
    if not ADMIN_WEBHOOK_URL:
        log.error("ADMIN_WEBHOOK_URL 미설정 — 에러 알림 생략: [%s] %s", stage, message)
        return
    when = now_kst().strftime("%Y-%m-%d %H:%M KST")
    try:
        _post(ADMIN_WEBHOOK_URL, build_error_card(stage, message, when))
    except Exception as e:  # noqa: BLE001
        log.error("관리자 에러 알림 전송조차 실패: %s", e)
