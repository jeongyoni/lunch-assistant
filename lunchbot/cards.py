"""Teams Adaptive Card 빌더. 모든 빌더는 webhook 전송용 message 봉투로 감싸 반환."""
from .utils import stars


def _wrap(card):
    """AdaptiveCard를 Power Automate Workflows webhook 형식으로 감싼다."""
    return {
        "type": "message",
        "attachments": [{
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": card,
        }],
    }


def _card(body, actions=None):
    c = {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.4",
        "body": body,
    }
    if actions:
        c["actions"] = actions
    return c


def build_daily_card(date_str, weekday, menu_items, analysis,
                     image_url=None, vote_url="", menu_page_url="",
                     allergens=None, tomorrow_label="", tomorrow_menu=None):
    body = [
        {"type": "TextBlock", "text": "🍱 오늘의 학식",
         "weight": "Bolder", "size": "Large"},
        {"type": "TextBlock", "text": f"{date_str} ({weekday})",
         "isSubtle": True, "spacing": "None", "wrap": True},
    ]

    if menu_items:
        body.append({"type": "TextBlock", "text": "오늘의 메뉴",
                     "weight": "Bolder", "spacing": "Medium"})
        body.append({"type": "TextBlock",
                     "text": "\n".join(f"• {m}" for m in menu_items),
                     "wrap": True, "spacing": "Small"})
    else:
        body.append({"type": "TextBlock",
                     "text": "오늘은 등록된 중식 메뉴가 없습니다 🍙",
                     "wrap": True, "spacing": "Medium"})

    # 알레르기 주의
    if allergens:
        body.append({"type": "TextBlock",
                     "text": "⚠️ 알레르기 주의: " + ", ".join(allergens),
                     "wrap": True, "spacing": "Small",
                     "color": "Warning", "weight": "Bolder"})

    if image_url:
        body.append({"type": "Image", "url": image_url,
                     "size": "Large", "altText": "오늘의 점심 이미지"})

    if analysis:
        facts = []
        if analysis.get("kcal") is not None:
            facts.append({"title": "🔥 예상 칼로리",
                          "value": f"약 {analysis['kcal']} kcal"})
        macro = " · ".join(x for x in [
            f"탄 {analysis['carb_g']}g" if analysis.get("carb_g") is not None else None,
            f"단 {analysis['protein_g']}g" if analysis.get("protein_g") is not None else None,
            f"지 {analysis['fat_g']}g" if analysis.get("fat_g") is not None else None,
        ] if x)
        if macro:
            facts.append({"title": "🍚 탄·단·지", "value": macro})
        if analysis.get("health_score") is not None:
            facts.append({"title": "💚 건강 점수",
                          "value": stars(analysis["health_score"])})
        recs = []
        if analysis.get("diet_friendly"):
            recs.append("🥗 다이어트 추천")
        if analysis.get("post_workout"):
            recs.append("💪 운동 후 추천")
        if recs:
            facts.append({"title": "👍 추천", "value": " / ".join(recs)})
        if facts:
            body.append({"type": "FactSet", "facts": facts, "spacing": "Medium"})

        if analysis.get("comment"):
            body.append({"type": "TextBlock", "text": f"🤖 {analysis['comment']}",
                         "wrap": True})
        if analysis.get("tags"):
            body.append({"type": "TextBlock",
                         "text": " ".join(f"#{t}" for t in analysis["tags"]),
                         "isSubtle": True, "size": "Small", "wrap": True})
        body.append({"type": "TextBlock", "text": "※ AI 추정치이며 참고용입니다.",
                     "isSubtle": True, "size": "Small", "wrap": True})

    # 힘나는 한마디
    cheer = (analysis or {}).get("cheer")
    if cheer:
        body.append({"type": "TextBlock", "text": f"💬 {cheer}",
                     "wrap": True, "spacing": "Medium", "weight": "Bolder",
                     "color": "Accent"})

    # 다음 급식일 미리보기
    if tomorrow_menu:
        preview = ", ".join(tomorrow_menu[:4])
        if len(tomorrow_menu) > 4:
            preview += " 외"
        label = f"🔜 {tomorrow_label} 메뉴" if tomorrow_label else "🔜 다음 메뉴"
        body.append({"type": "TextBlock", "text": f"{label}: {preview}",
                     "wrap": True, "spacing": "Medium", "isSubtle": True})

    actions = []
    if menu_page_url:
        actions.append({"type": "Action.OpenUrl", "title": "📄 학식 페이지 보기",
                        "url": menu_page_url})
    if vote_url:
        actions.append({"type": "Action.OpenUrl", "title": "😋 만족도 투표",
                        "url": vote_url})

    return _wrap(_card(body, actions or None))


def build_error_card(stage, message, when):
    body = [
        {"type": "TextBlock", "text": "🚨 학식봇 오류", "weight": "Bolder",
         "size": "Large", "color": "Attention"},
        {"type": "FactSet", "facts": [
            {"title": "단계", "value": str(stage)},
            {"title": "시각", "value": str(when)},
        ]},
        {"type": "TextBlock", "text": str(message), "wrap": True},
    ]
    return _wrap(_card(body))


def build_weekly_card(summary):
    body = [
        {"type": "TextBlock", "text": "📊 이번 주 학식 리포트",
         "weight": "Bolder", "size": "Large"},
        {"type": "TextBlock", "text": summary.get("period", ""),
         "isSubtle": True, "spacing": "None"},
    ]
    facts = [{"title": "집계된 날", "value": f"{summary.get('days', 0)}일"}]
    if summary.get("avg_health") is not None:
        facts.append({"title": "평균 건강점수", "value": stars(summary["avg_health"])})
    if summary.get("healthiest"):
        facts.append({"title": "가장 건강했던 날", "value": summary["healthiest"]})
    if summary.get("heaviest"):
        facts.append({"title": "가장 칼로리 높은 날", "value": summary["heaviest"]})
    body.append({"type": "FactSet", "facts": facts, "spacing": "Medium"})

    if summary.get("top_menus"):
        body.append({"type": "TextBlock", "text": "🏆 이달의 인기 메뉴 TOP",
                     "weight": "Bolder", "spacing": "Medium"})
        body.append({"type": "TextBlock",
                     "text": "\n".join(f"{i + 1}. {n} ({c}회)"
                                       for i, (n, c) in enumerate(summary["top_menus"])),
                     "wrap": True, "spacing": "Small"})
    return _wrap(_card(body))
