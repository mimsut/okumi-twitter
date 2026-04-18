#!/usr/bin/env python3
"""
오꿈이 트위터 콘텐츠 자동 생성기
Gemini (무료) + 실시간 트렌드로 오꿈이 스타일 트윗 10개 생성 → Discord 전송
"""

import os
import random
import requests
import datetime
from google import genai
from bs4 import BeautifulSoup

DISCORD_WEBHOOK_URL = (
    "https://discord.com/api/webhooks/1494971650847014913/"
    "QEfp8_ssBU4MJfQa-SWTV-ko9AtdPk3Psjpmn5Jz_FXhIz7cdb2Nopg5O5phoHQ1A6RQ"
)

# ── 실시간 트렌드 스크래핑 ────────────────────────────────────────────────────

def get_naver_trends() -> list[str]:
    """네이버 실시간 급상승 검색어 (DataLab JSON)"""
    try:
        r = requests.get(
            "https://datalab.naver.com/keyword/realtimeList.naver?where=main",
            headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://www.naver.com",
                "X-Requested-With": "XMLHttpRequest",
            },
            timeout=8,
        )
        data = r.json()
        keywords = [item["keyword"] for item in data.get("ranks", [])]
        if keywords:
            return keywords[:10]
    except Exception:
        pass
    return []


def get_daum_trends() -> list[str]:
    """다음 실시간 인기 검색어"""
    try:
        r = requests.get(
            "https://search.daum.net/search?w=tot&DA=SBC&t__nil_searchbox=btn&sug=&sugo=&q=",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=8,
        )
        soup = BeautifulSoup(r.text, "html.parser")
        items = soup.select(".rank_news .tit_item") or soup.select("a.link_issue")
        keywords = [el.get_text(strip=True) for el in items if el.get_text(strip=True)]
        if keywords:
            return keywords[:10]
    except Exception:
        pass
    return []


def get_trends() -> list[str]:
    """트렌드 소스 순차 시도 → 전부 실패 시 Gemini가 직접 판단"""
    for fn in [get_naver_trends, get_daum_trends]:
        result = fn()
        if result:
            print(f"[트렌드] {fn.__name__}: {result}")
            return result
    print("[트렌드] 스크래핑 실패 → Gemini가 현재 트렌드 추론")
    return []  # 빈 리스트면 Gemini가 알아서


# ── Gemini 트윗 생성 ─────────────────────────────────────────────────────────

SYSTEM_PROMPT = """너는 트위터 계정 오꿈이야. 오리의 꿈 앱 마스코트인데 그냥 트위터 폐인임.
디시인사이드 눈팅 10년차, 트위터 중독자, 밈 고인물.

[절대 하지 마]
- "후회는 내일의 나에게!" 이런 거 ㄴㄴ 개구려
- "~인 듯 ㅜㅜ" "~네요" "~습니다" ㄴㄴ
- 위로, 힐링, 응원 ㄴㄴ 아무도 안 물어봄
- 말 길게 늘이기 ㄴㄴ. 짧고 세게
- 이모지 남발 ㄴㄴ. 🦆 가끔만
- 브랜드 계정 티 내기 ㄴㄴ

[말투]
- 디시/트위터 고인물처럼: ㅋㅋ ㄹㅇ ㅇㅈ 존나 개- 씨 아 진짜 등 자연스럽게
- 문장 짧게 끊기. 호흡 빠르게
- 공감은 구체적으로. 추상적인 공감 ㄴㄴ
- 드립은 예상 못 한 방향으로
- 말이 되는 거 써. 억지 조합 ㄴㄴ

[참고할 실제 트윗 문체]
"치킨 먹으면서 오늘부터 다이어트 해야지 하는 뇌 구조가 궁금함"
"알람 5개 맞춰놓고 다 끄는 사람이랑 알람 1개로 일어나는 사람은 다른 종족임"
"아니 진짜 왜 누우면 갑자기 3년 전 일이 생각나냐 이게 무슨 고문이야"
"회의 중에 갑자기 딴 생각하다가 이름 불리는 순간 심장 쿵 내려앉은 사람"
"편의점 도시락 고르는 데 15분 쓰는 거 나만임?"
"오늘 존나 힘들었는데 집 오는 길에 고양이 봤더니 기분 나아짐. 고양이한테 지배당하는 중"
"야 근데 진짜로 주말이 왜 이렇게 빨리 가냐 평일은 왜 이렇게 느리냐 시간이 나 싫어하냐"
"모르는 번호 전화 와서 안 받았더니 문자도 없음. 뭐야 나한테 왜 전화함"
"""


def generate_tweets(trends: list[str]) -> list[str]:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError("GEMINI_API_KEY 환경 변수가 없음. aistudio.google.com에서 무료 발급")

    client = genai.Client(api_key=api_key)

    kst = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)
    weekdays = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
    weekday = weekdays[kst.weekday()]
    time_str = kst.strftime(f"%Y년 %m월 %d일 {weekday} %H:%M")

    if trends:
        trend_context = f"지금 한국에서 실시간으로 핫한 키워드: {', '.join(trends)}\n이 중 자연스럽게 어울리는 것만 골라서 써."
    else:
        trend_context = "실시간 트렌드 데이터 없음. 지금 이 시간대에 한국 트위터에서 공감될 만한 주제로 자유롭게 써."

    prompt = f"""{SYSTEM_PROMPT}

현재 시각: {time_str}
{trend_context}

트윗 10개 써줘.
규칙:
- 텍스트만. 번호 따옴표 없이
- 빈 줄로 구분
- 10개 다 다른 주제/형식
- 말 되게. 억지 없이
- 짧고 세게. 한 문장~두 문장"""

    response = client.models.generate_content(model="models/gemini-2.5-flash", contents=prompt)
    raw = response.text.strip()

    tweets = []
    for line in raw.split("\n"):
        line = line.strip()
        if not line:
            continue
        # 번호 제거 (1. 2. 혹은 1) 등)
        import re
        line = re.sub(r"^\d+[\.\)]\s*", "", line)
        if line:
            tweets.append(line)

    return tweets[:10]


# ── Discord 전송 ──────────────────────────────────────────────────────────────

def send_to_discord(tweets: list[str], trends: list[str]):
    kst = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)
    now_str = kst.strftime("%Y.%m.%d %H:%M KST")
    trend_str = " · ".join(trends[:6]) if trends else "Gemini 자체 추론"

    lines = [
        f"🦆 **오꿈이 트윗 초안** `{now_str}`",
        f"📈 트렌드: `{trend_str}`",
        "─────────────────────────────────",
        "",
    ]
    for i, t in enumerate(tweets, 1):
        lines.append(f"**{i}.** {t}")
    lines += ["", "─────────────────────────────────", "_골라서 올려줘 ✏️_"]

    full_msg = "\n".join(lines)
    chunks, cur = [], ""
    for line in full_msg.split("\n"):
        if len(cur) + len(line) + 1 > 1900:
            chunks.append(cur.rstrip())
            cur = line + "\n"
        else:
            cur += line + "\n"
    if cur.strip():
        chunks.append(cur.rstrip())

    for chunk in chunks:
        r = requests.post(DISCORD_WEBHOOK_URL, json={"content": chunk}, timeout=10)
        status = "OK" if r.status_code in (200, 204) else f"실패 {r.status_code}"
        print(f"[Discord {status}] {len(chunk)}자")


# ── 메인 ─────────────────────────────────────────────────────────────────────

def main():
    kst = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)
    print(f"\n{'='*50}")
    print(f"오꿈이 트윗 생성: {kst.strftime('%Y-%m-%d %H:%M KST')}")
    print(f"{'='*50}")

    trends = get_trends()
    tweets = generate_tweets(trends)

    print(f"\n[생성된 트윗 {len(tweets)}개]")
    for i, t in enumerate(tweets, 1):
        print(f"  {i}. {t}")

    send_to_discord(tweets, trends)
    print("\n완료!\n")


if __name__ == "__main__":
    main()
