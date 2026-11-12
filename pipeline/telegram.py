"""텔레그램 승인: 후보 발송 + 버튼 응답 수집 (서버 없이 폴링)"""
import html
import requests
from .config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"


def _call(method, http_timeout=30, **params):
    r = requests.post(f"{API}/{method}", json=params, timeout=http_timeout)
    r.raise_for_status()
    return r.json()["result"]


def send_candidate(item):
    text = (
        f"<b>{html.escape(item.get('hook', ''))}</b>\n"
        f"{html.escape(item['title'])}\n"
        f"<i>{html.escape(item.get('source', ''))} · 점수 {item.get('score', '-')}</i>\n"
        f"💡 {html.escape(item.get('reason', ''))}\n"
        f"<a href=\"{html.escape(item['link'])}\">원문</a>"
    )
    kb = {"inline_keyboard": [[
        {"text": "✅ 승인", "callback_data": f"ok:{item['id']}"},
        {"text": "❌ 거절", "callback_data": f"no:{item['id']}"},
    ]]}
    _call("sendMessage", chat_id=TELEGRAM_CHAT_ID, text=text,
          parse_mode="HTML", reply_markup=kb, disable_web_page_preview=True)


def notify(text):
    _call("sendMessage", chat_id=TELEGRAM_CHAT_ID, text=text)


def fetch_decisions(offset, wait=0):
    """버튼 응답을 읽어 [(action, item_id)]와 새 offset 반환.
    wait초 동안 버튼 누르기를 기다림 (0이면 바로 확인만)"""
    updates = _call("getUpdates", http_timeout=wait + 20, offset=offset, timeout=wait,
                    allowed_updates=["callback_query"])
    decisions = []
    for u in updates:
        offset = u["update_id"] + 1
        cq = u.get("callback_query")
        if not cq or ":" not in cq.get("data", ""):
            continue
        # 본인 채팅에서 온 것만 인정
        if str(cq["message"]["chat"]["id"]) != str(TELEGRAM_CHAT_ID):
            continue
        action, iid = cq["data"].split(":", 1)
        if action not in ("ok", "no"):
            continue
        decisions.append((action, iid))
        label = "✅ 승인됨" if action == "ok" else "❌ 거절됨"
        try:
            _call("answerCallbackQuery", callback_query_id=cq["id"], text=label)
            _call("editMessageReplyMarkup", chat_id=cq["message"]["chat"]["id"],
                  message_id=cq["message"]["message_id"],
                  reply_markup={"inline_keyboard": [[{"text": label, "callback_data": "noop:x"}]]})
        except requests.HTTPError:
            pass  # 오래된 버튼은 응답 표시가 실패할 수 있음 — 결정은 그대로 반영
    return decisions, offset
