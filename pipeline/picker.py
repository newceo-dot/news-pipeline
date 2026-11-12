"""Picker: Gemini로 카드뉴스 후보 선별"""
import json
import requests
from .config import GEMINI_API_KEY, GEMINI_MODEL, PICK_COUNT

PROMPT = """너는 한국 개인투자자 대상 인스타그램 투자뉴스 계정 MARKET 7의 카드뉴스 편집자다.
아래 뉴스 목록에서 카드뉴스로 만들 가치가 큰 기사 {n}개를 골라라.

선정 기준:
- 개인투자자 다수에게 영향이 큰 거시/시장 뉴스 우선 (금리, 환율, 지수, 비트코인, 정책, 대형 이슈)
- 같은 사건은 하나만
- 특정 종목 매수/매도 권유로 읽힐 소재, 루머성 기사는 제외

JSON 배열만 출력. 각 원소:
{{"id": "목록의 id", "score": 1~10 정수, "reason": "선정 이유 한 줄", "hook": "카드 1장 제목용 훅 문구 20자 이내"}}

뉴스 목록:
{items}
"""


def pick(items):
    if not items:
        return []
    listing = "\n".join(
        f"- id={i['id']} | {i['title']} | {i['source']}" for i in items[:120]
    )
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    body = {
        "contents": [{"parts": [{"text": PROMPT.format(n=PICK_COUNT, items=listing)}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.3},
    }
    r = requests.post(url, params={"key": GEMINI_API_KEY}, json=body, timeout=180)
    r.raise_for_status()
    text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
    picks = json.loads(text)

    by_id = {i["id"]: i for i in items}
    result = []
    for p in sorted(picks, key=lambda x: -int(x.get("score", 0))):
        base = by_id.get(p.get("id"))
        if base:
            result.append({**base, **p})
    print(f"[picker] 선별 {len(result)}건")
    return result[:PICK_COUNT]
