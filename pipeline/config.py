import os
from pathlib import Path
from dotenv import load_dotenv

import shutil

ROOT = Path(__file__).resolve().parent.parent
IS_CI = os.getenv("GITHUB_ACTIONS") == "true"

if IS_CI:
    # GitHub에서는 저장소 안에 보관
    ENV_PATH = ROOT / ".env"
    DATA = ROOT / "data"
else:
    # 내 PC에서는 프로그램 폴더와 분리된 고정 위치에 보관
    # → 새 버전을 어디에 풀어도 설정·기록이 그대로 유지됨
    HOME_DIR = Path.home() / "news-pipeline-config"
    ENV_PATH = HOME_DIR / ".env"
    DATA = HOME_DIR / "data"
    HOME_DIR.mkdir(exist_ok=True)
    if not ENV_PATH.exists():
        # 예전 버전 폴더에 있던 설정·기록을 자동으로 찾아 옮겨옴
        for folder in (ROOT, ROOT.parent, ROOT.parent.parent):
            old = folder / ".env"
            if old.exists():
                shutil.copy(old, ENV_PATH)
                if (folder / "data").is_dir():
                    shutil.copytree(folder / "data", DATA, dirs_exist_ok=True)
                print(f"(예전 설정을 가져왔어요: {folder})")
                break

DATA.mkdir(exist_ok=True)
load_dotenv(ENV_PATH)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
COLLECT_INTERVAL_HOURS = float(os.getenv("COLLECT_INTERVAL_HOURS", "12"))
PICK_COUNT = int(os.getenv("PICK_COUNT", "5"))

# 수집할 RSS. 자유롭게 추가/삭제
FEEDS = [
    # 구글뉴스 한국 비즈니스 헤드라인
    "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=ko&gl=KR&ceid=KR:ko",
    # 키워드 검색형 (증시 / 환율 / 금리 / ETF, 최근 1일)
    "https://news.google.com/rss/search?q=%EC%A6%9D%EC%8B%9C+when:1d&hl=ko&gl=KR&ceid=KR:ko",
    "https://news.google.com/rss/search?q=%ED%99%98%EC%9C%A8+when:1d&hl=ko&gl=KR&ceid=KR:ko",
    "https://news.google.com/rss/search?q=%EA%B8%88%EB%A6%AC+when:1d&hl=ko&gl=KR&ceid=KR:ko",
    "https://news.google.com/rss/search?q=ETF+when:1d&hl=ko&gl=KR&ceid=KR:ko",
]
