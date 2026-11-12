"""실행 순서
① 텔레그램 버튼 결과 반영 (후보 승인/거절, 카드 발행/취소)
② 승인된 뉴스 → 카드뉴스 만들고 미리보기 발송
③ 주기가 되면 새 후보 수집·선별·발송
④ 처리할 게 남아 있으면 일정 시간 버튼을 실시간으로 받아줌
"""
import sys
import time
from pipeline import store, collector, picker, telegram
from pipeline.config import COLLECT_INTERVAL_HOURS

WATCH_MINUTES = 15
MAX_CARDS_PER_RUN = 5


def process_decisions(wait=0):
    state = store.load("state", {"tg_offset": 0, "last_collect": 0})
    pending = store.load("pending", {})
    queue = store.load("queue", [])
    by_id = {q["id"]: q for q in queue}

    decisions, state["tg_offset"] = telegram.fetch_decisions(state["tg_offset"], wait)
    for action, iid in decisions:
        if action in ("ok", "no"):
            item = pending.pop(iid, None)
            if item and action == "ok":
                item["status"] = "approved"
                item["approved_at"] = int(time.time())
                queue.append(item)
                by_id[iid] = item
            print("  ✅ 후보 승인" if action == "ok" else "  ❌ 후보 거절")
        elif iid in by_id:
            # 카드 미리보기 버튼: 발행 승인 / 취소
            by_id[iid]["status"] = "publish_ready" if action == "pub" else "canceled"
            print("  📤 발행 대기 등록" if action == "pub" else "  🗑 카드 취소")

    store.save("state", state)
    store.save("pending", pending)
    store.save("queue", queue)
    waiting = len(pending) + sum(q["status"] in ("approved", "previewed") for q in queue)
    return state, waiting


def make_cards():
    """승인된 뉴스를 카드뉴스로 만들고 미리보기 발송"""
    from pipeline import writer, cards   # 이미지 라이브러리는 필요할 때만 불러옴
    queue = store.load("queue", [])
    todo = [q for q in queue if q["status"] == "approved"][:MAX_CARDS_PER_RUN]
    for item in todo:
        print(f"[cards] 만드는 중: {item['title'][:30]}...")
        try:
            script = writer.write(item)
            files = cards.render(item, script)
            telegram.send_preview(item, script, files)
            item["script"] = script
            item["cards"] = [str(f.relative_to(f.parents[3])) for f in files]
            item["status"] = "previewed"
        except Exception as e:  # 한 건 실패해도 나머지는 계속
            item["fail_count"] = item.get("fail_count", 0) + 1
            print(f"  실패: {e}")
            if item["fail_count"] >= 3:
                item["status"] = "failed"
                telegram.notify(f"⚠️ 카드 만들기 3번 실패해서 건너뜀: {item['title'][:40]}")
        store.save("queue", queue)   # 한 건마다 저장


def collect_and_send(state, force=False):
    due = time.time() - state.get("last_collect", 0) >= COLLECT_INTERVAL_HOURS * 3600
    if not (due or force):
        return False
    items = collector.collect()
    picks = picker.pick(items)
    pending = store.load("pending", {})
    for p in picks:
        telegram.send_candidate(p)
        pending[p["id"]] = p
    if picks:
        telegram.notify(f"오늘의 후보 {len(picks)}건입니다. 승인할 것만 ✅ 눌러주세요.")
    state["last_collect"] = int(time.time())
    store.save("pending", pending)
    store.save("state", state)
    return bool(picks)


def watch():
    print(f"\n텔레그램 버튼을 기다리는 중... (최대 {WATCH_MINUTES}분, 다 처리되면 자동 종료)")
    end = time.time() + WATCH_MINUTES * 60
    while time.time() < end:
        _, left = process_decisions(wait=25)
        make_cards()
        if left == 0:
            print("모두 처리 완료!")
            return
    print("시간이 지나 종료합니다. 나중에 누른 버튼은 다음 실행 때 반영돼요.")


if __name__ == "__main__":
    from pipeline import config
    missing = [k for k in ("GEMINI_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID")
               if not getattr(config, k)]
    if missing:
        sys.exit("\n설정이 비어 있어요: " + ", ".join(missing)
                 + "\n→ 1_setup.bat 을 다시 실행해서 마지막 '설치 완료'까지 진행해 주세요.")
    force = "--now" in sys.argv
    st, _ = process_decisions()
    make_cards()
    sent = collect_and_send(st, force=force)
    if sent or "--watch" in sys.argv:
        watch()
    print("\n완료!")
