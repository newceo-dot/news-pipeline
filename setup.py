"""설치 도우미 — 질문에 답만 하면 .env 설정 파일을 자동으로 만들어 줍니다."""
import sys
import time
from pathlib import Path
import requests

from pipeline.config import ENV_PATH as ENV

# 모델 자동 선택 시 제외할 특수 용도 모델
SKIP = ("lite", "image", "tts", "audio", "live", "embedding", "vision", "thinking", "exp")


def ask(msg):
    while True:
        v = input(msg).strip()
        if v:
            return v
        print("  → 비어 있어요. 다시 입력해 주세요.")


def check_telegram(token):
    r = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=20)
    if r.status_code != 200 or not r.json().get("ok"):
        return None
    return r.json()["result"]["username"]


def find_chat_id(token):
    # allowed_updates를 꼭 지정해야 함: 지정 안 하면 텔레그램이 이전 설정(버튼만 받기)을 그대로 써서
    # 메시지가 안 보임
    r = requests.post(f"https://api.telegram.org/bot{token}/getUpdates",
                      json={"allowed_updates": ["message", "callback_query"]}, timeout=20)
    data = r.json()
    if not data.get("ok"):
        print(f"  (텔레그램 응답: {data.get('description')})")
    for u in reversed(data.get("result", [])):
        msg = u.get("message") or u.get("edited_message")
        if not msg and u.get("callback_query"):
            msg = u["callback_query"].get("message")
        if msg and msg["chat"]["type"] == "private":
            return str(msg["chat"]["id"]), msg["chat"].get("first_name", "")
    return None, None


def pick_gemini_model(key):
    base = "https://generativelanguage.googleapis.com/v1beta"
    r = requests.get(f"{base}/models", params={"key": key, "pageSize": 200}, timeout=20)
    if r.status_code != 200:
        return None, f"키 확인 실패 ({r.status_code}): {r.text[:200]}"
    names = [m["name"].split("/")[-1] for m in r.json().get("models", [])
             if "generateContent" in m.get("supportedGenerationMethods", [])]
    flash = [n for n in names if "flash" in n and not any(s in n for s in SKIP)]
    # 정식 버전 우선, 최신(이름 내림차순) 우선, preview는 뒤로
    flash = sorted(flash, key=lambda n: ("preview" in n, [-ord(c) for c in n]))
    for name in flash:
        print(f"  - {name} 테스트 중...")
        try:
            t = requests.post(f"{base}/models/{name}:generateContent", params={"key": key},
                              json={"contents": [{"parts": [{"text": "OK"}]}],
                                    "generationConfig": {"maxOutputTokens": 5}},
                              timeout=40)
        except requests.RequestException:
            print("    응답이 늦어서 건너뜀")
            continue
        if t.status_code == 200:
            return name, None
        print(f"    사용 불가({t.status_code}) → 다음 모델")
    return None, "무료로 응답하는 Flash 모델을 찾지 못했어요."


def load_env():
    d = {}
    if ENV.exists():
        for line in ENV.read_text(encoding="utf-8").splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                d[k.strip()] = v.strip()
    return d


def save_env(d):
    ENV.write_text("".join(f"{k}={v}\n" for k, v in d.items()), encoding="utf-8")


def main():
    print("\n=== 투자뉴스 파이프라인 설치 도우미 (v4) ===\n")
    env = load_env()
    env.setdefault("COLLECT_INTERVAL_HOURS", "12")
    env.setdefault("PICK_COUNT", "5")

    # 이전에 텔레그램 설정을 마쳤으면 건너뛰기
    if env.get("TELEGRAM_BOT_TOKEN") and env.get("TELEGRAM_CHAT_ID") \
            and check_telegram(env["TELEGRAM_BOT_TOKEN"]):
        print("① 텔레그램: 이전 설정 사용 ✔")
        token, chat_id = env["TELEGRAM_BOT_TOKEN"], env["TELEGRAM_CHAT_ID"]
        return finish_gemini(env, token, chat_id)

    # 1) 텔레그램
    while True:
        token = ask("① 텔레그램 봇 토큰을 붙여넣고 Enter: ")
        bot = check_telegram(token)
        if bot:
            print(f"  ✔ 봇 확인: @{bot}")
            break
        print("  ✘ 토큰이 맞지 않아요. 복사할 때 앞뒤 공백 없이 전부 복사했는지 확인해 주세요.")

    # 2) 채팅 ID 자동 탐지
    chat_id, name = find_chat_id(token)
    tries = 0
    while not chat_id:
        tries += 1
        if tries > 2:
            v = input("\n  자동으로 못 찾았어요. 채팅 ID 숫자를 직접 입력하고 Enter: ").strip()
            if v.lstrip("-").isdigit():
                chat_id, name = v, "직접 입력"
                break
        print(f"\n  텔레그램에서 @{bot} 대화창을 열고 '안녕'이라고 보내주세요.")
        input("  보냈으면 Enter: ")
        time.sleep(2)
        chat_id, name = find_chat_id(token)
    print(f"  ✔ 내 채팅 찾음: {name} ({chat_id})")
    env["TELEGRAM_BOT_TOKEN"], env["TELEGRAM_CHAT_ID"] = token, chat_id
    save_env(env)   # 여기까지 저장 → 다음에 다시 실행하면 이 단계는 건너뜀
    finish_gemini(env, token, chat_id)


def finish_gemini(env, token, chat_id):
    while True:
        key = ask("\n② Gemini API 키를 붙여넣고 Enter: ")
        print("  모델 확인 중... (1~2분 걸릴 수 있어요)")
        model, err = pick_gemini_model(key)
        if model:
            print(f"  ✔ 사용할 모델: {model}")
            break
        print(f"  ✘ {err}")

    env["GEMINI_API_KEY"], env["GEMINI_MODEL"] = key, model
    save_env(env)
    requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                  json={"chat_id": chat_id, "text": "✅ 설치 완료! 이제 '2_run.bat'을 눌러보세요."},
                  timeout=20)
    print("\n🎉 설치 완료! 텔레그램에 확인 메시지를 보냈어요.")
    print("   다음: '2_run.bat'을 더블클릭하세요.\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit("\n취소했어요.")
    except requests.RequestException as e:
        sys.exit(f"\n인터넷 연결 문제로 멈췄어요: {e}")
