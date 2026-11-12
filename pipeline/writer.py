"""Writer: 승인된 뉴스로 카드뉴스 원고 작성 (Gemini + 구글 검색 확인)"""
import json
import re
import requests
from .config import GEMINI_API_KEY, GEMINI_MODEL

PROMPT = """너는 한국 개인투자자 대상 인스타그램 카드뉴스 작가다.
아래 뉴스를 구글 검색으로 먼저 확인한 뒤, 확인된 사실로만 원고를 써라.

뉴스 제목: {title}
언론사: {source}
보도 시각: {published}

규칙:
- 검색으로 확인된 사실과 숫자만 쓴다. 확인 못 한 내용은 쓰지 않는다.
- 기사 문장을 그대로 옮기지 말고, 투자 초보도 이해하게 쉬운 말로 새로 쓴다.
- 특정 종목을 사라/팔라는 표현, 수익 보장 표현 금지.
- 핵심을 제대로 확인하지 못했으면 "verified": false.

아래 JSON만 출력 (코드블록, 설명 없이):
{{
  "cover_title": "표지 큰 제목, 18자 이내, 호기심 유발",
  "cover_sub": "표지 부제, 30자 이내",
  "slides": [
    {{"title": "무슨 일이 있었나?", "body": "120자 이내"}},
    {{"title": "왜 중요할까?", "body": "120자 이내"}},
    {{"title": "투자자가 볼 포인트", "body": "120자 이내, 권유 아닌 관찰 포인트"}}
  ],
  "caption": "인스타·스레드 본문 250자 이내. 마지막 줄에 해시태그 5개",
  "verified": true
}}
"""


def _call(item, grounded):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    body = {
        "contents": [{"parts": [{"text": PROMPT.format(**{
            "title": item["title"], "source": item.get("source", ""),
            "published": item.get("published", "")})}]}],
        "generationConfig": {"temperature": 0.3},
    }
    if grounded:
        body["tools"] = [{"google_search": {}}]
    r = requests.post(url, params={"key": GEMINI_API_KEY}, json=body, timeout=180)
    r.raise_for_status()
    cand = r.json()["candidates"][0]
    text = "".join(p.get("text", "") for p in cand["content"]["parts"])
    m = re.search(r"\{.*\}", text, re.S)  # 앞뒤 군더더기 제거
    data = json.loads(m.group(0))

    sources = []
    for ch in cand.get("groundingMetadata", {}).get("groundingChunks", [])[:3]:
        w = ch.get("web", {})
        if w.get("uri"):
            sources.append({"title": w.get("title", "출처"), "uri": w["uri"]})
    data["sources"] = sources
    return data


def write(item):
    """원고 dict 반환. 검색 확인 실패 시 검색 없이 작성하고 경고 표시"""
    try:
        data = _call(item, grounded=True)
        data["grounded"] = bool(data["sources"])
    except (requests.HTTPError, ValueError, KeyError, AttributeError) as e:
        print(f"  검색 확인 모드 실패 → 일반 모드로 작성 ({e})")
        data = _call(item, grounded=False)
        data["grounded"] = False
    if not data["grounded"]:
        data["verified"] = False
    return data
