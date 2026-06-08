"""일자별 캐시(data/YYYY-MM-DD.json)와 이미지 경로 관리.

캐시 파일 존재 = 그날 OpenAI 호출 완료 → 재호출 금지(비용 절감).
notified 플래그 = 이미 Teams 전송 완료 → 중복 전송 방지.
"""
import os
import json
import logging

from .config import DATA_DIR, IMAGE_DIR, GH_OWNER, GH_REPO, GH_BRANCH

log = logging.getLogger(__name__)


def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(IMAGE_DIR, exist_ok=True)


def cache_path(date_str):
    return os.path.join(DATA_DIR, f"{date_str}.json")


def image_path(date_str):
    return os.path.join(IMAGE_DIR, f"{date_str}.png")


def image_url(date_str):
    # ?v= 캐시버스터: Teams 이미지 프록시의 과거 캐시 방지
    return (
        f"https://raw.githubusercontent.com/{GH_OWNER}/{GH_REPO}/"
        f"{GH_BRANCH}/{IMAGE_DIR}/{date_str}.png?v={date_str}"
    )


def load(date_str):
    p = cache_path(date_str)
    if not os.path.exists(p):
        return None
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        log.warning("캐시 읽기 실패(%s), 무시: %s", p, e)
        return None


def save(date_str, payload):
    ensure_dirs()
    with open(cache_path(date_str), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    log.info("캐시 저장: %s", cache_path(date_str))
