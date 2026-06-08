"""모든 설정을 한곳에서 관리. 값은 환경변수(GitHub Secrets/Variables)로 주입."""
import os
from zoneinfo import ZoneInfo

# ── 시간대: 러너는 UTC라서 반드시 KST로 고정 ──
KST = ZoneInfo("Asia/Seoul")
WEEKDAYS = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
WEEKDAYS_SHORT = ["월", "화", "수", "목", "금", "토", "일"]

# ── 스크래핑 대상 (광명융합기술교육원 학식 페이지) ──
# kopo.ac.kr/gm/ 의 'gm'이 광명 캠퍼스. menu 번호는 페이지가 바뀌면 갱신.
MENU_URL = os.environ.get(
    "MENU_URL",
    "https://www.kopo.ac.kr/gm/content.do?menu=12623",
)

# ── 저장 경로 (저장소에 커밋되는 영역) ──
DATA_DIR = "data"      # data/YYYY-MM-DD.json
IMAGE_DIR = "images"   # images/YYYY-MM-DD.png

# ── 이미지 raw URL 구성 (본인 저장소로 교체) ──
GH_OWNER = os.environ.get("GH_OWNER", "your-github-id")
GH_REPO = os.environ.get("GH_REPO", "lunch-assistant")
GH_BRANCH = os.environ.get("GH_BRANCH", "main")

# ── 시크릿 ──
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
TEAMS_WEBHOOK_URL = os.environ.get("TEAMS_WEBHOOK_URL")
# 관리자 알림용 (미설정 시 일반 채널과 동일하게 사용)
ADMIN_WEBHOOK_URL = os.environ.get("ADMIN_WEBHOOK_URL") or TEAMS_WEBHOOK_URL
# 만족도 투표용 폼/플로우 URL (선택)
VOTE_URL = os.environ.get("VOTE_URL", "")

# ── 동작 옵션 ──
ENABLE_IMAGE = os.environ.get("ENABLE_IMAGE", "true").lower() == "true"
# 이미지 품질: low < medium < high (비용 차이 큼)
IMAGE_QUALITY = os.environ.get("IMAGE_QUALITY", "medium")
# 캐시 무시하고 강제 재실행/재전송
FORCE = os.environ.get("FORCE", "false").lower() == "true"

# ── OpenAI 모델 ──
TEXT_MODEL = os.environ.get("OPENAI_TEXT_MODEL", "gpt-4o-mini")
IMAGE_MODEL = os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-1")

SCRAPE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}
