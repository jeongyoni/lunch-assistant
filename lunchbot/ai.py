"""OpenAI 연동: 메뉴 영양 분석(텍스트) + 급식 이미지 생성."""
import json
import base64
import logging

from .config import OPENAI_API_KEY, TEXT_MODEL, IMAGE_MODEL, IMAGE_QUALITY
from .errors import OpenAIError
from .utils import request_with_retry

log = logging.getLogger(__name__)


def _headers():
    return {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }


def analyze_menu(menu_items, weekday=""):
    """메뉴를 분석해 칼로리·탄단지·건강점수·추천여부·코멘트·응원을 JSON으로 반환.

    주의: 스키마 예시에 '실제 숫자'를 넣으면 작은 모델이 그 값을 그대로 복사해버려
    매일 같은 결과가 나온다. 그래서 예시는 모두 '자리표시자(placeholder)'로 두고,
    값은 반드시 이 메뉴를 근거로 새로 계산하도록 명시한다.
    """
    menu_str = ", ".join(menu_items)
    day_line = f"오늘은 {weekday}입니다.\n" if weekday else ""
    prompt = (
        "너는 한국 구내식당 메뉴를 평가하는 영양사야. "
        "아래 '오늘 메뉴'만 보고 한 끼 기준 영양을 추정해서 평가해줘. "
        "정확한 측정값이 아니라, 이 메뉴 구성에 맞는 합리적인 어림값이면 돼.\n"
        f"{day_line}"
        f"오늘 메뉴: {menu_str}\n\n"
        "반드시 지킬 것:\n"
        "- 모든 숫자는 위 '오늘 메뉴'를 근거로 직접 산출해. 메뉴가 다르면 숫자도 달라져야 해.\n"
        "- 아래 형식의 값들은 '예시'일 뿐이다. 예시의 숫자나 문구를 그대로 복사하지 마.\n"
        "- 설명 문장 없이 JSON 객체만 출력해.\n\n"
        "출력 형식 (꺾쇠 안은 채워 넣을 자리이며, 예시 값을 재사용하지 말 것):\n"
        "{\n"
        '  "kcal": <한 끼 총열량을 나타내는 정수>,\n'
        '  "carb_g": <탄수화물 g 정수>,\n'
        '  "protein_g": <단백질 g 정수>,\n'
        '  "fat_g": <지방 g 정수>,\n'
        '  "health_score": <1~5 사이 정수, 5가 가장 건강>,\n'
        '  "comment": "<이 메뉴에 맞춘 1~2문장 평가>",\n'
        '  "diet_friendly": <true 또는 false>,\n'
        '  "post_workout": <true 또는 false>,\n'
        '  "tags": ["<짧은 키워드>", "<짧은 키워드>"],\n'
        '  "cheer": "<오늘 메뉴와 요일을 살린 따뜻한 응원 한마디>"\n'
        "}\n\n"
        "추가 규칙:\n"
        "- kcal/carb_g/protein_g/fat_g 는 모두 정수.\n"
        "- comment 는 1~2문장, 이 메뉴의 실제 구성(주메뉴·국·반찬)을 반영할 것.\n"
        "- tags 는 2~4개의 짧은 키워드.\n"
        "- cheer 는 1문장, 오늘 메뉴/요일을 살려 매번 다르게.\n"
        "- 다시 강조: 예시 숫자(자리표시자)를 그대로 쓰지 말고 메뉴 기준으로 계산할 것."
    )
    try:
        r = request_with_retry(
            "POST",
            "https://api.openai.com/v1/chat/completions",
            headers=_headers(),
            json={
                "model": TEXT_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.6,
                "response_format": {"type": "json_object"},
            },
            timeout=30,
        )
        raw = r.json()["choices"][0]["message"]["content"]
        data = json.loads(raw)
    except Exception as e:  # noqa: BLE001
        raise OpenAIError(f"메뉴 분석 실패: {e}") from e

    return _normalize(data)


def _normalize(d):
    """모델 응답에 키가 빠지거나 타입이 어긋나도 카드가 안전하도록 보정."""
    def _int(v):
        try:
            return int(round(float(v)))
        except (TypeError, ValueError):
            return None

    return {
        "kcal": _int(d.get("kcal")),
        "carb_g": _int(d.get("carb_g")),
        "protein_g": _int(d.get("protein_g")),
        "fat_g": _int(d.get("fat_g")),
        "health_score": _int(d.get("health_score")) or 3,
        "comment": str(d.get("comment", "")).strip(),
        "diet_friendly": bool(d.get("diet_friendly", False)),
        "post_workout": bool(d.get("post_workout", False)),
        "tags": [str(t).strip() for t in (d.get("tags") or []) if str(t).strip()][:4],
        "cheer": str(d.get("cheer", "")).strip(),
    }


def generate_image(menu_items, save_path):
    """급식 사진풍 이미지를 생성해 save_path(png)로 저장."""
    menu_str = ", ".join(menu_items)
    prompt = (
        "한국 학교 급식 스테인리스 6칸 배식판을 바로 위에서 내려다본 실제 사진. "
        "배식판 구조: 아래쪽에 큰 칸 2개(왼쪽 밥칸, 오른쪽 국칸), "
        "그 위 좌우에 깊은 반찬칸 1개씩, 가운데에 얕은 반찬칸 2개. "
        f"각 칸에 담긴 음식: {menu_str}. "
        "왼쪽 아래 큰 칸에는 밥, 오른쪽 아래 큰 칸에는 국물 요리. "
        "반찬은 칸마다 색과 형태가 분명히 다르게, 김치는 붉고 매콤한 색으로 구분. "
        "형광등 아래 급식실 분위기, 실제 DSLR 음식 사진, 일러스트나 3D 렌더링 아님."
    )
    try:
        r = request_with_retry(
            "POST",
            "https://api.openai.com/v1/images/generations",
            headers=_headers(),
            json={
                "model": IMAGE_MODEL,
                "prompt": prompt,
                "size": "1024x1024",
                "quality": IMAGE_QUALITY,  # low / medium / high
                "n": 1,
            },
            timeout=120,
        )
        b64 = r.json()["data"][0]["b64_json"]
    except Exception as e:  # noqa: BLE001
        raise OpenAIError(f"이미지 생성 실패: {e}") from e

    with open(save_path, "wb") as f:
        f.write(base64.b64decode(b64))
    log.info("이미지 저장: %s", save_path)