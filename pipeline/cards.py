"""Cards: 원고를 1080x1350(인스타 세로 4:5) JPEG 카드로 그리기 — 화이트 미니멀"""
import datetime as dt
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from .config import ACCOUNT_NAME, DATA

W, H = 1080, 1350
M = 96                      # 좌우 여백
BG = "#FFFFFF"
INK = "#111111"
SUB = "#6B6B6B"
LINE = "#E6E6E6"
ACCENT = "#2F5BEA"          # 포인트 색 하나만

# 폰트 후보: 윈도우(맑은 고딕) / 리눅스(GitHub, Noto) / 맥
FONTS = {
    "bold": [("C:/Windows/Fonts/malgunbd.ttf", 0),
             ("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", 1),
             ("/System/Library/Fonts/AppleSDGothicNeo.ttc", 6)],
    "regular": [("C:/Windows/Fonts/malgun.ttf", 0),
                ("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 1),
                ("/System/Library/Fonts/AppleSDGothicNeo.ttc", 0)],
}


def font(kind, size):
    for path, idx in FONTS[kind]:
        if Path(path).exists():
            return ImageFont.truetype(path, size, index=idx)
    raise FileNotFoundError("한글 폰트를 찾지 못했어요.")


def wrap(draw, text, f, max_w):
    """한글은 글자 단위, 공백 기준으로 자연스럽게 줄바꿈"""
    lines = []
    for para in text.split("\n"):
        line = ""
        for word in para.split(" "):
            cand = (line + " " + word).strip()
            if draw.textlength(cand, font=f) <= max_w:
                line = cand
                continue
            if line:
                lines.append(line)
            line = ""
            for ch in word:  # 단어 하나가 너무 길면 글자 단위로
                if draw.textlength(line + ch, font=f) > max_w:
                    lines.append(line)
                    line = ""
                line += ch
        lines.append(line)
    return lines


def text_block(draw, xy, text, f, fill, max_w, gap=1.5):
    x, y = xy
    for ln in wrap(draw, text, f, max_w):
        draw.text((x, y), ln, font=f, fill=fill)
        y += int(f.size * gap)
    return y


def frame(page, total):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    today = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).strftime("%m.%d")
    d.text((M, 80), f"오늘의 투자뉴스 · {today}", font=font("regular", 30), fill=SUB)
    d.text((W - M, 80), f"{page}/{total}", font=font("regular", 30), fill=SUB, anchor="ra")
    d.line((M, H - 130, W - M, H - 130), fill=LINE, width=2)
    if ACCOUNT_NAME:
        d.text((M, H - 100), ACCOUNT_NAME, font=font("bold", 30), fill=INK)
    return img, d


def render(item, script):
    out = DATA / "cards" / item["id"]
    out.mkdir(parents=True, exist_ok=True)
    slides = script["slides"]
    total = len(slides) + 2
    paths = []
    maxw = W - 2 * M

    # 1) 표지
    img, d = frame(1, total)
    d.rectangle((M, 330, M + 80, 338), fill=ACCENT)
    y = text_block(d, (M, 380), script["cover_title"], font("bold", 92), INK, maxw, 1.3)
    text_block(d, (M, y + 40), script["cover_sub"], font("regular", 42), SUB, maxw)
    d.text((W - M, H - 100), "넘겨서 보기 →", font=font("regular", 30), fill=SUB, anchor="ra")
    paths.append(img)

    # 2) 본문
    for i, s in enumerate(slides, start=1):
        img, d = frame(i + 1, total)
        d.text((M, 260), f"{i:02d}", font=font("bold", 64), fill=ACCENT)
        y = text_block(d, (M, 370), s["title"], font("bold", 62), INK, maxw, 1.3)
        d.line((M, y + 30, M + 80, y + 30), fill=INK, width=4)
        text_block(d, (M, y + 80), s["body"], font("regular", 44), INK, maxw, 1.65)
        paths.append(img)

    # 3) 마무리
    img, d = frame(total, total)
    y = text_block(d, (M, 330), "매일 아침\n투자뉴스를 정리해요", font("bold", 72), INK, maxw, 1.35)
    if ACCOUNT_NAME:
        d.text((M, y + 40), f"팔로우 {ACCOUNT_NAME}", font=font("bold", 40), fill=ACCENT)
    src = item.get("source") or "언론 보도"
    note = (f"출처: {src} 보도 및 공개 자료 재구성\n"
            "본 콘텐츠는 정보 제공 목적이며 투자 권유가 아닙니다. "
            "투자 판단과 책임은 본인에게 있습니다.")
    text_block(d, (M, H - 400), note, font("regular", 30), SUB, maxw, 1.6)
    paths.append(img)

    files = []
    for n, im in enumerate(paths, start=1):
        p = out / f"{n}.jpg"
        im.save(p, "JPEG", quality=92)  # 인스타 발행은 JPEG만 가능
        files.append(p)
    return files
