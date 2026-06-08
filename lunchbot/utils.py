"""날짜/포맷/네트워크 재시도 같은 공통 헬퍼."""
import time
import datetime

from .config import KST, WEEKDAYS


def now_kst():
    return datetime.datetime.now(KST)


def today_str(dt=None):
    return (dt or now_kst()).strftime("%Y-%m-%d")


def weekday_name(dt=None):
    return WEEKDAYS[(dt or now_kst()).weekday()]


def is_weekday(dt=None):
    return (dt or now_kst()).weekday() < 5


def stars(score, out_of=5):
    """건강 점수(1~5)를 ★★★★☆ 형태로."""
    try:
        s = max(0, min(out_of, int(round(float(score)))))
    except (TypeError, ValueError):
        return "정보 없음"
    return "★" * s + "☆" * (out_of - s)


def request_with_retry(method, url, *, tries=3, backoff=2, **kwargs):
    """일시적 네트워크 오류에 대비한 재시도 래퍼."""
    import requests  # 지연 임포트
    last = None
    for i in range(tries):
        try:
            r = requests.request(method, url, **kwargs)
            r.raise_for_status()
            return r
        except Exception as e:  # noqa: BLE001
            last = e
            if i < tries - 1:
                time.sleep(backoff * (i + 1))
    raise last
