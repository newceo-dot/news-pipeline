"""Collector: RSS에서 뉴스 소재 수집 + 중복 제거"""
import hashlib
import time
import feedparser
from .config import FEEDS
from . import store

MAX_SEEN = 3000


def _id(link: str) -> str:
    return hashlib.sha1(link.encode()).hexdigest()[:12]


def collect():
    seen = set(store.load("seen", []))
    items, titles = [], set()
    for url in FEEDS:
        feed = feedparser.parse(url)
        for e in feed.entries[:30]:
            link = e.get("link", "")
            title = e.get("title", "").strip()
            if not link or not title:
                continue
            iid = _id(link)
            key = title[:25]  # 같은 기사 여러 매체 중복 대충 제거
            if iid in seen or key in titles:
                continue
            titles.add(key)
            src = e.get("source")
            source = src.get("title", "") if src else ""
            items.append({
                "id": iid,
                "title": title,
                "link": link,
                "source": source,
                "published": e.get("published", ""),
                "collected_at": int(time.time()),
            })
    seen_list = list(seen) + [i["id"] for i in items]
    store.save("seen", seen_list[-MAX_SEEN:])
    print(f"[collector] 새 소재 {len(items)}건")
    return items
