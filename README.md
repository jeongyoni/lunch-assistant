# 🍱 AI 학식 비서 (한국폴리텍대학 광명융합기술교육원)

GitHub Actions가 평일 아침 학식 메뉴를 스크래핑하고, OpenAI로 영양·건강도를 분석하고
급식 이미지를 생성해 Teams 채널에 Adaptive Card로 보냅니다. 주간 리포트도 자동 발송합니다.

---

## 아키텍처

```
[GitHub Actions cron] ─평일 09:00 KST─▶ run.py build
        │                                   │
        │                       1) 학식 페이지 스크래핑 (scraper)
        │                       2) OpenAI 영양/건강 분석 (ai.analyze_menu)
        │                       3) OpenAI 급식 이미지 생성 (ai.generate_image)
        │                       4) data/날짜.json + images/날짜.png 저장 (cache)
        ▼
   git commit & push  ──▶ raw.githubusercontent 에 이미지 공개
        │
        ▼
   run.py notify ──▶ 캐시 로드 → Adaptive Card → Teams webhook (teams.send_card)
        │
        ▼
   notified=true 저장 & push (중복 전송 방지)

[GitHub Actions cron] ─금요일 17:00 KST─▶ run.py weekly
        └▶ data/*.json 누적분 집계 → 주간 리포트 카드 전송
```

핵심 설계 두 가지:
- **build → push → notify 분리**: Teams는 카드를 받는 순간 이미지 URL을 가져가 캐싱하므로,
  이미지를 먼저 push해 공개한 뒤에 전송해야 깨지지 않습니다.
- **KST 고정**: 러너는 UTC라 `datetime.now()`가 요일을 틀리게 합니다. `Asia/Seoul`로 통일.

---

## 폴더 구조

```
lunch-assistant/
├── .github/workflows/
│   ├── daily-lunch.yml       # 평일 09:00 일일 알림
│   └── weekly-summary.yml    # 금요일 17:00 주간 리포트
├── lunchbot/
│   ├── config.py             # 환경변수·경로·모델·옵션 (단일 진실 공급원)
│   ├── errors.py             # 단계별 예외 (scrape/menu-empty/openai/teams)
│   ├── utils.py              # KST 날짜, 별점, 재시도
│   ├── scraper.py            # 메뉴 수집 + 없음/실패 구분
│   ├── ai.py                 # 영양 분석 + 이미지 생성
│   ├── cache.py              # data/*.json 읽기·쓰기, 이미지 경로/URL
│   ├── cards.py              # Adaptive Card 빌더 (일일/에러/주간)
│   ├── teams.py              # 전송 + 관리자 에러 알림
│   └── analytics.py          # 주간 요약 / 월간 인기 메뉴
├── data/                     # 일자별 캐시 (커밋됨)
├── images/                   # 생성 이미지 (커밋됨)
├── samples/daily-card.json   # 카드 출력 예시
├── run.py                    # 엔트리포인트 (build/notify/weekly)
└── requirements.txt
```

---

## 설정

**Secrets** (Settings ▸ Secrets and variables ▸ Actions ▸ Secrets)
| 이름 | 설명 |
|---|---|
| `OPENAI_API_KEY` | OpenAI API 키 |
| `TEAMS_WEBHOOK_URL` | 알림 채널 webhook (Power Automate **Workflows**) |
| `ADMIN_WEBHOOK_URL` | 에러 알림용 (생략 시 위와 동일) |

**Variables** (같은 화면 ▸ Variables)
| 이름 | 예시 | 설명 |
|---|---|---|
| `MENU_URL` | `https://www.kopo.ac.kr/gm/content.do?menu=12623` | 광명융합기술교육원 학식 페이지 |
| `VOTE_URL` | `https://forms.office.com/r/...` | 만족도 투표 폼 (선택) |
| `IMAGE_QUALITY` | `low` / `medium` / `high` | 이미지 품질=비용 |
| `ENABLE_IMAGE` | `true` / `false` | 이미지 생성 on/off |

`GH_OWNER/REPO/BRANCH`는 워크플로우가 자동으로 채웁니다.

---

## 캐시 구조 (`data/2026-06-08.json`)

```json
{
  "date": "2026-06-08",
  "weekday": "월요일",
  "menu": ["제육볶음", "미역국", "김치", "잡곡밥"],
  "analysis": {
    "kcal": 750, "carb_g": 90, "protein_g": 32, "fat_g": 26,
    "health_score": 4, "comment": "단백질이 충분해 운동 후 식사로 적합합니다",
    "diet_friendly": false, "post_workout": true,
    "tags": ["고단백", "국물포함"]
  },
  "image_url": "https://raw.githubusercontent.com/.../images/2026-06-08.png?v=2026-06-08",
  "notified": true
}
```

- 파일 존재 = 그날 OpenAI 호출 완료 → **재실행해도 재호출 안 함**(비용 절감).
- `notified` = 전송 완료 → **중복 전송 방지**.

---

## 에러 처리 구조

| 상황 | 분류 | 동작 |
|---|---|---|
| 페이지 요청/파싱 실패 | `ScrapeError` | 관리자 알림 후 종료(실패 표시) |
| 오늘 메뉴 없음(휴무) | `MenuNotFoundError` | 장애 아님 → "메뉴 없음" 카드 전송 |
| OpenAI 분석/이미지 실패 | `OpenAIError` | 해당 부분만 생략, 메뉴는 그대로 전송 |
| Teams 전송 실패 | `TeamsError` | 관리자 알림 후 종료 |
| 그 외 | `fatal` | 트레이스백 로그 + 관리자 알림 |

관리자 알림은 `ADMIN_WEBHOOK_URL`로 별도 카드 전송하며, 알림 전송 자체가
실패해도 로그만 남기고 무한 루프에 빠지지 않습니다.

---

## 💰 비용 절감

- **이미지가 비용의 대부분**입니다. 텍스트 분석(`gpt-4o-mini`)은 매우 저렴.
- `IMAGE_QUALITY=low` 또는 `medium`으로 낮추면 이미지 단가가 크게 떨어집니다.
- 정 아끼려면 `ENABLE_IMAGE=false`로 이미지를 끄거나, 주 1회만 켜는 식으로 운용.
- 캐시 덕분에 같은 날 재실행해도 추가 과금이 없습니다.
- 정확한 단가는 변동되니 OpenAI 공식 가격 페이지에서 현재 요율을 확인하세요.

---

## ⚠️ GitHub Actions 주의점

- **cron은 정시 보장이 안 됩니다.** 특히 정각(00분)은 혼잡해 5~15분 이상 밀릴 수 있어요.
  정확도가 필요하면 `5 0 * * 1-5`처럼 분을 살짝 띄우세요.
- **공개 저장소에서 60일간 커밋이 없으면 스케줄이 자동 비활성화**됩니다.
  이 봇은 매일 커밋을 남기므로 자연스럽게 유지되지만, 비활성화되면 수동 실행으로 깨우면 됩니다.
- 워크플로우가 push하려면 `permissions: contents: write`가 필요합니다(설정돼 있음).
- 봇 커밋이 다시 워크플로우를 트리거하지 않도록, push 트리거(`on: push`)는 쓰지 않았습니다.
- **이미지 커밋이 쌓이면 저장소가 커집니다.** 아래 유지보수 참고.

---

## 🔧 유지보수

- **학식 페이지 구조가 바뀌면** `scraper.py`의 칼럼 탐지/요일 매칭만 손보면 됩니다.
  헤더에서 '중식'을 찾고 없으면 index 2로 폴백하도록 돼 있습니다.
- **오래된 이미지 정리**: 저장소 비대화를 막으려면 주기적으로 `images/`의 옛 파일을
  지우는 cleanup 스텝을 추가하거나(예: 60일 경과분 삭제), 이미지를 릴리스 에셋으로 옮기세요.
- **로컬 테스트**: `MENU_URL` 등 환경변수를 셸에 export하고 `python run.py build` →
  `python run.py notify` 순으로 실행. (이미지 URL은 push 전이라 안 뜰 수 있음)
- **모델 교체**: `OPENAI_TEXT_MODEL` / `OPENAI_IMAGE_MODEL` 환경변수로 바꿀 수 있습니다.

---

## 한계 (정직하게)

- **만족도 투표·학생 반응 수집**: 들어오는 Teams *webhook*은 단방향 전송 전용이라
  버튼 응답을 직접 받지 못합니다. 그래서 투표 버튼은 외부 폼/플로우(`VOTE_URL`,
  예: Microsoft Forms)로 연결했습니다. 실제 응답을 모아 **만족도 기반 랭킹**을 만들려면
  Forms 응답을 읽거나 Power Automate HTTP 트리거로 받는 추가 연동이 필요합니다.
- 지금 구현된 랭킹은 응답이 필요 없는 **AI 건강점수·칼로리 기반** 통계입니다.
- 메뉴 표 구조는 학교마다 달라, 실제 광명융합기술교육원 페이지 HTML에 맞춰 `scraper.py`를
  한 번 조정해야 할 수 있습니다.

## 추가 기능 (v1.1)

- **알레르기 주의 표시**: 메뉴 이름에서 흔한 알레르기 식품(돼지/소/닭/계란/우유/새우/게/생선/견과/밀 등)을 키워드로 감지해 카드에 강조. *키워드 기반이라 100% 정확하진 않으니 참고용입니다 — 심각한 알레르기는 반드시 식당에 직접 확인하세요.* 키워드는 `lunchbot/allergens.py`에서 자유롭게 수정/추가할 수 있습니다.
- **다음 급식일 미리보기**: 같은 표에서 다음 급식일 메뉴를 함께 읽어 "🔜 ○요일 메뉴: …" 한 줄로 표시. 금요일이면 자동으로 월요일을 가리킵니다.
- **힘나는 한마디**: AI가 그날 메뉴·요일에 맞춰 응원 문구를 생성(기존 영양 분석 호출에 필드만 추가해 추가 비용 거의 없음). `OPENAI_API_KEY`가 동작해야 표시됩니다.
