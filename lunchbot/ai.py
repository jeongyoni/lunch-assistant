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


def analyze_menu(menu_items):
    """메뉴를 분석해 칼로리·탄단지·건강점수·추천여부·코멘트를 JSON으로 반환."""
    menu_str = ", ".join(menu_items)
    prompt = (
        "다음은 한국 구내식당의 점심 메뉴입니다. 한 끼 기준으로 영양을 추정하고 평가해줘. "
        "정확한 측정값이 아니라 합리적인 어림값이면 됩니다.\n"
        f"메뉴: {menu_str}\n\n"
        "반드시 아래 JSON 스키마로만, 다른 설명 없이 답해:\n"
        "{\n"
        '  "kcal": 750,\n'
        '  "carb_g": 90, "protein_g": 30, "fat_g": 25,\n'
        '  "health_score": 4,\n'
        '  "comment": "단백질이 충분하고 운동 후 식사로 적합합니다",\n'
        '  "diet_friendly": false,\n'
        '  "post_workout": true,\n'
        '  "tags": ["고단백", "국물포함"]\n'
        "}\n"
        "- kcal/carb_g/protein_g/fat_g: 정수\n"
        "- health_score: 1~5 정수(5가 가장 건강)\n"
        "- comment: 1~2문장\n"
        "- diet_friendly/post_workout: true 또는 false\n"
        "- tags: 짧은 키워드 2~4개"
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
