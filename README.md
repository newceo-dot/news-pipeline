# 투자뉴스 카드뉴스 파이프라인 — 1단계

수집(RSS) → Gemini 선별 → 텔레그램 승인 → `data/queue.json`에 승인 목록 저장.
2단계(카드뉴스 이미지 + 스레드/인스타 발행)는 이 queue를 가져다 씁니다.

## 가장 쉬운 사용법 (윈도우)
1. `1_setup.bat` 더블클릭 → 질문에 답하기 (처음 한 번만)
2. `2_run.bat` → 텔레그램으로 후보 도착
3. 텔레그램에서 ✅/❌ 누른 뒤 `3_approve.bat`

설정과 기록은 `내 사용자 폴더\news-pipeline-config`에 따로 보관됩니다. 새 버전은 아무 데나 풀어서 실행해도 됩니다.

## 준비물 (전부 무료)
1. **Gemini API 키**: https://aistudio.google.com 에서 발급. 현재 무료로 쓸 수 있는 Flash 계열 모델명을 확인해 `GEMINI_MODEL`에 넣기.
   - 무료 티어 입력·출력은 Google 모델 개선에 쓰일 수 있음 → 공개 뉴스만 넣으므로 문제 없음.
2. **텔레그램 봇**: 텔레그램에서 @BotFather → `/newbot` → 토큰 받기.
3. **내 채팅 ID**: 만든 봇에게 아무 메시지 보낸 뒤 브라우저에서
   `https://api.telegram.org/bot<토큰>/getUpdates` 열고 `"chat":{"id": 숫자}` 확인.

## 내 PC에서 테스트
```bash
pip install -r requirements.txt
cp .env.example .env      # 값 채우기
python main.py --now      # 즉시 수집 → 텔레그램으로 후보 도착
# 텔레그램에서 ✅/❌ 누른 뒤
python main.py            # 승인 결과가 data/queue.json에 반영
```

## GitHub Actions로 자동 운영
1. GitHub에 **공개(Public)** 저장소 생성 후 이 폴더 push
2. Settings → Secrets and variables → Actions
   - Secrets: `GEMINI_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`
   - Variables(선택): `GEMINI_MODEL`
3. Actions 탭 → news-pipeline → Run workflow (now=true)로 첫 실행 확인
4. 이후 30분마다 자동 실행, 12시간마다 새 후보 발송

⚠️ 키는 절대 코드/.env를 커밋하지 말 것 (.gitignore에 포함됨).

## 운영 원칙
- 기사 문장을 그대로 옮기지 말고 요약·재작성 + 출처 표기 (2단계 프롬프트에 반영 예정)
- 특정 종목 매수/매도 권유 금지, "투자 권유 아님" 문구 고정
