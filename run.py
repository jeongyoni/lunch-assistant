"""엔트리포인트.

사용법:
  python run.py build    # 스크래핑 + AI 분석/이미지 → 캐시 저장 (전송 안 함)
  python run.py notify   # 캐시를 읽어 Teams 전송 (이미지 push 후 호출)
  python run.py weekly   # 주간 리포트 전송
  python run.py          # build + notify (로컬 테스트용; 이미지는 push 전이라 안 뜰 수 있음)
"""
import sys
import logging
import traceback

from lunchbot import config, cache, scraper, ai, cards, teams, analytics
from lunchbot.errors import ScrapeError, MenuNotFoundError, OpenAIError, TeamsError
from lunchbot.utils import today_str, weekday_name

log = logging.getLogger("run")


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


# ── build: 스크래핑 + AI 생성 + 캐시 저장 ──
def cmd_build():
    cache.ensure_dirs()
    date = today_str()

    if cache.load(date) and not config.FORCE:
        log.info("캐시 존재 — OpenAI 재호출 생략 (%s)", date)
        return

    # 1) 스크래핑
    try:
        menu = scraper.fetch_today_menu()
    except MenuNotFoundError as e:
        # 휴무/미등록은 장애가 아님: 빈 메뉴로 캐시만 남겨 재시도 방지
        log.warning("메뉴 없음: %s", e)
        cache.save(date, {"date": date, "weekday": weekday_name(),
                          "menu": [], "analysis": None,
                          "image_url": None, "notified": False})
        return
    except ScrapeError as e:
        log.error("스크래핑 실패: %s", e)
        teams.send_admin_error(ScrapeError.stage, str(e))
        sys.exit(1)

    # 2) AI 분석 (실패해도 메뉴 전송은 계속)
    analysis = None
    if config.OPENAI_API_KEY:
        try:
            analysis = ai.analyze_menu(menu)
            log.info("AI 분석: %s", analysis)
        except OpenAIError as e:
            log.error("AI 분석 실패(계속 진행): %s", e)
            teams.send_admin_error("openai-analyze", str(e))
    else:
        log.info("OPENAI_API_KEY 없음 — AI 분석 생략")

    # 3) 이미지 (실패해도 계속)
    image_url = None
    if config.OPENAI_API_KEY and config.ENABLE_IMAGE:
        try:
            ai.generate_image(menu, cache.image_path(date))
            image_url = cache.image_url(date)
        except OpenAIError as e:
            log.error("이미지 생성 실패(계속 진행): %s", e)
            teams.send_admin_error("openai-image", str(e))

    cache.save(date, {"date": date, "weekday": weekday_name(),
                      "menu": menu, "analysis": analysis,
                      "image_url": image_url, "notified": False})


# ── notify: 캐시 읽어 Teams 전송 + 중복 전송 방지 ──
def cmd_notify():
    date = today_str()
    rec = cache.load(date)

    if rec is None:
        log.warning("캐시 없음 — 즉석 스크래핑으로 전송(이미지 없음)")
        try:
            menu = scraper.fetch_today_menu()
        except MenuNotFoundError:
            menu = []
        except ScrapeError as e:
            teams.send_admin_error(ScrapeError.stage, str(e))
            sys.exit(1)
        rec = {"menu": menu, "analysis": None, "image_url": None,
               "notified": False, "weekday": weekday_name()}

    if rec.get("notified") and not config.FORCE:
        log.info("이미 전송됨 — 중복 전송 방지 (%s)", date)
        return

    card = cards.build_daily_card(
        date, rec.get("weekday", weekday_name()),
        rec.get("menu", []), rec.get("analysis"),
        image_url=rec.get("image_url"),
        vote_url=config.VOTE_URL, menu_page_url=config.MENU_URL,
    )
    try:
        teams.send_card(card)
    except TeamsError as e:
        log.error("Teams 전송 실패: %s", e)
        teams.send_admin_error(TeamsError.stage, str(e))
        sys.exit(1)

    rec["notified"] = True
    cache.save(date, rec)


# ── weekly: 주간 리포트 ──
def cmd_weekly():
    summary = analytics.weekly_summary()
    if summary["days"] == 0:
        log.info("집계할 데이터가 없어 주간 리포트 생략")
        return
    try:
        teams.send_card(cards.build_weekly_card(summary))
    except TeamsError as e:
        teams.send_admin_error("teams-weekly", str(e))
        sys.exit(1)


def main():
    setup_logging()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    try:
        if cmd == "build":
            cmd_build()
        elif cmd == "notify":
            cmd_notify()
        elif cmd == "weekly":
            cmd_weekly()
        else:
            cmd_build()
            cmd_notify()
    except SystemExit:
        raise
    except Exception as e:  # noqa: BLE001 — 최후의 방어선
        log.error("예기치 못한 오류:\n%s", traceback.format_exc())
        try:
            teams.send_admin_error("fatal", str(e))
        except Exception:  # noqa: BLE001
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
