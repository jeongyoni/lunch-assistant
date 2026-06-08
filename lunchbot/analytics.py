"""누적된 data/*.json 캐시를 읽어 주간 요약과 월간 인기 메뉴를 집계."""
import os
import json
import glob
import logging
import datetime
from collections import Counter

from .config import DATA_DIR, KST, WEEKDAYS_SHORT

log = logging.getLogger(__name__)


def _load_range(start, end):
    """[start, end] 사이 날짜의 캐시 레코드를 로드."""
    out = []
    for p in sorted(glob.glob(os.path.join(DATA_DIR, "*.json"))):
        name = os.path.splitext(os.path.basename(p))[0]
        try:
            d = datetime.date.fromisoformat(name)
        except ValueError:
            continue
        if start <= d <= end:
            try:
                with open(p, encoding="utf-8") as f:
                    rec = json.load(f)
            except (OSError, json.JSONDecodeError):
                continue
            rec["_date"] = d
            out.append(rec)
    return out


def _label(d):
    return f"{d.strftime('%m/%d')}({WEEKDAYS_SHORT[d.weekday()]})"


def weekly_summary(today=None):
    """이번 주(월~금) 건강 통계 + 이달 인기 메뉴 TOP."""
    today = today or datetime.datetime.now(KST).date()
    monday = today - datetime.timedelta(days=today.weekday())
    friday = monday + datetime.timedelta(days=4)

    week = [r for r in _load_range(monday, friday) if r.get("menu")]

    summary = {
        "period": f"{monday.strftime('%Y-%m-%d')} ~ {friday.strftime('%m-%d')}",
        "days": len(week),
        "avg_health": None,
        "healthiest": None,
        "heaviest": None,
        "top_menus": [],
    }
    if not week:
        return summary

    scores = [(r, (r.get("analysis") or {}).get("health_score")) for r in week]
    valid = [(r, s) for r, s in scores if isinstance(s, (int, float))]
    if valid:
        summary["avg_health"] = round(sum(s for _, s in valid) / len(valid), 1)
        best = max(valid, key=lambda x: x[1])[0]
        summary["healthiest"] = _label(best["_date"])

    kcals = [(r, (r.get("analysis") or {}).get("kcal")) for r in week]
    kcals = [(r, k) for r, k in kcals if isinstance(k, (int, float))]
    if kcals:
        heavy = max(kcals, key=lambda x: x[1])
        summary["heaviest"] = f"{_label(heavy[0]['_date'])} (약 {heavy[1]} kcal)"

    # 월간 인기 메뉴 (이번 달 1일 ~ 오늘)
    month_start = today.replace(day=1)
    counter = Counter()
    for r in _load_range(month_start, today):
        for item in r.get("menu", []):
            # 밥/국물 같은 공통 항목은 제외해 변별력 확보
            if item.endswith(("밥", "국", "탕")) or item in ("김치", "깍두기"):
                continue
            counter[item] += 1
    summary["top_menus"] = counter.most_common(5)

    return summary
