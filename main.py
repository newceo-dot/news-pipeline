"""실행 순서: ① 밀린 승인 반영 ② 주기가 되면 새 후보 발송 ③ 일정 시간 버튼을 바로바로 처리"""
import sys
import time
from pipeline import store, collector, picker, telegram
from pipeline.config import COLLECT_INTERVAL_HOURS

WATCH_MINUTES = 15   # 후보를 보낸 뒤 버튼을 실시간으로 받아줄 시간


def process_decisions(wait=0):
    state = store.load("state", {"tg_offset": 0, "last_collect": 0})
    pending = store.load("pending", {})
    queue = store.load("queue", [])

    decisions, state["tg_offset"] = telegram.fetch_decisions(state["tg_offset"], wait)
    for action, iid in decisions:
        item = pending.pop(iid, None)
        if item and action == "ok":
            item["status"] = "approved"     # 2단계(카드뉴스 생성)가 이 상태를 가져감
            item["approved_at"] = int(time.time())
            queue.append(item)
    for action, _ in decisions:
        print("  ✅ 승인 1건" if action == "ok" else "  ❌ 거절 1건")

    store.save("state", state)
    store.save("pending", pending)
    store.save("queue", queue)
    return state, len(pending)


def watch():
    """후보를 보낸 뒤, 버튼을 누르는 즉시 반영. 전부 처리되거나 시간이 지나면 종료"""
    print(f"\n텔레그램에서 ✅/❌를 눌러주세요. (최대 {WATCH_MINUTES}분 기다림, 다 누르면 자동 종료)")
    end = time.time() + WATCH_MINUTES * 60
    while time.time() < end:
        _, left = process_decisions(wait=25)
        if left == 0:
            print("모든 후보 처리 완료!")
            return
    print(f"시간이 지나 종료합니다. 남은 후보는 나중에 눌러도 다음 실행 때 반영돼요.")


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


if __name__ == "__main__":
    from pipeline import config
    missing = [k for k in ("GEMINI_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID")
               if not getattr(config, k)]
    if missing:
        sys.exit("\n설정이 비어 있어요: " + ", ".join(missing)
                 + "\n→ 1_setup.bat 을 다시 실행해서 마지막 '설치 완료'까지 진행해 주세요.")
    force = "--now" in sys.argv
    st, _ = process_decisions()
    sent = collect_and_send(st, force=force)
    if sent or "--watch" in sys.argv:
        watch()
    print("\n완료!")
