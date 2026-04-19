#!/usr/bin/env python3
"""
오꿈이 트위터 콘텐츠 자동 생성기
Gemini Google Search grounding으로 실시간 트렌드 + 실제 트윗 말투 학습
"""

import os
import re
import requests
import datetime
from google import genai
from google.genai import types

DISCORD_WEBHOOK_URL = (
    "https://discord.com/api/webhooks/1494971650847014913/"
    "QEfp8_ssBU4MJfQa-SWTV-ko9AtdPk3Psjpmn5Jz_FXhIz7cdb2Nopg5O5phoHQ1A6RQ"
)
MODEL = "models/gemini-2.5-flash"

def get_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError("GEMINI_API_KEY 없음")
    return genai.Client(api_key=api_key)

def _extract_text(response) -> str:
    """응답에서 텍스트 안전하게 추출 (None 방어)"""
    if response.text:
        return response.text.strip()
    # candidates에서 직접 추출 시도
    try:
        for candidate in response.candidates:
            for part in candidate.content.parts:
                if hasattr(part, "text") and part.text:
                    return part.text.strip()
    except Exception:
        pass
    return ""

def grounded(client, prompt: str) -> str:
    """Google Search grounding으로 실시간 웹 정보 포함해서 생성"""
    try:
        r = client.models.generate_content(
            model=MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            ),
        )
        return _extract_text(r)
    except Exception as e:
        print(f"[grounded 실패] {e}")
        return ""

def generate_only(client, prompt: str) -> str:
    """검색 없이 순수 생성만"""
    r = client.models.generate_content(model=MODEL, contents=prompt)
    return _extract_text(r)

# ── Step 1: 실시간 트렌드 가져오기 ──────────────────────────────────────────

def get_trends(client) -> list[str]:
    kst = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)
    time_str = kst.strftime("%Y년 %m월 %d일 %H:%M")

    raw = grounded(
        client,
        f"오늘({time_str}) 한국 트위터 X 실시간 트렌드 검색해서 상위 키워드 10개만 알려줘. "
        "각 줄에 키워드 하나. 번호나 설명 없이 키워드만. "
        "예: 오드투러브\n크리스탈\n뮤뱅 1위"
    )
    print(f"[트렌드 raw]\n{raw}\n")

    trends = []
    for line in raw.split("\n"):
        line = line.strip()
        line = re.sub(r"^\d+[\.\)\-\*]\s*", "", line)
        line = line.lstrip("#").strip()
        line = re.sub(r"\*+", "", line).strip()
        if line and 1 < len(line) < 40 and not line.startswith("현재") and not line.startswith("지금"):
            trends.append(line)

    print(f"[트렌드] {trends[:10]}")
    return trends[:10]

# ── Step 2: 트렌드 관련 실제 트윗 샘플 수집 ─────────────────────────────────

def get_tweet_samples(client, trends: list[str]) -> str:
    top = trends[:3]
    raw = grounded(
        client,
        f"트위터(X)에서 {', '.join(top)} 관련해서 실제로 올라온 한국어 트윗 10개 찾아줘. "
        "재밌거나 공감되거나 드립 있는 트윗 위주로. "
        "트윗 본문만 줄바꿈으로. 말투와 이모지 그대로 유지해. "
        "혐오·욕설·공격적인 내용은 제외. 번호나 인용부호 없이 텍스트만."
    )
    print(f"[트윗 샘플 수집 완료] {len(raw)}자")
    return raw

# ── Step 3: 오꿈이 트윗 생성 ─────────────────────────────────────────────────

PERSONA = """너는 트위터 계정 오꿈이야. 오리의 꿈 앱 마스코트인데 트위터 폐인.

━━ 실제 한국 트위터 말투 핵심 ━━

[문장 구조]
- 마침표 거의 안 씀. 대신 ㅋㅋ로 끝내거나 그냥 끊음
- "아니 근데 ~", "근데 진짜", "아 씨", "야 근데" 로 시작
- "이거 나만임?", "나만 그래?", "이게 맞나", "왜임" 으로 끝내기
- 생각 중간에 끊기는 느낌: 그래서 뭐 어쩌라고 식의 호흡

[2025 트위터 현용 어휘]
- 국룰, 레전드, 핵공감, 현타, 킹받음, 갓생, ㄹㅇ, TMI인데, 아 진짜
- 순삭, 존나, 개-, 씨, 아 씨, 뭐임, 이게 맞냐, 왜이럼
- "~하는 사람 나야" 대신 "이거 나잖아" 또는 "이거 나임"
- ㅋㅋ는 두 개짜리 자주, 네 개 이상은 진짜 웃길 때만

[좋은 예시 - 이 느낌으로]
"배달 최저주문금액 채우려고 필요도 없는 거 담는 거 이게 맞냐ㅋㅋ"
"아니 충전기 꽂았는데 충전 안 되고 있던 거 발견하는 그 현타"
"편의점 1+1 있을 때만 신상 나오는 거 국룰임? 맨날 이럼"
"릴스 보다가 시간 순삭됐는데 본 거 하나도 기억 안 남 이게 뭐임"
"오늘 할 일 내일로 미루는 게 진짜 갓생 계획임 내일의 내가 할거니까"
"지하철에서 자리 양보했더니 서있으면서 받아먹는 사람 이거 뭐임"
"아니 카카오 또 먹통이야? 카카오가 대한민국 인프라였다는 거 이럴 때 실감함"
"월요일 생각하면 안 되는데 자꾸 생각남 이게 뇌 배신 아님?"

[절대 금지]
- "젠장" "이런" 같은 할아버지 감탄사
- 마침표로 끝나는 깔끔한 문장
- 위로, 힐링, 응원 멘트
- 혐오·특정인 공격
- 죽음·자해 표현 (멘탈케어 앱)
- 억지 오리 드립
"""

def generate_tweets(client, trends: list[str], samples: str) -> list[str]:
    kst = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)
    weekdays = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]
    time_str = kst.strftime(f"%H:%M {weekdays[kst.weekday()]}")

    prompt = f"""{PERSONA}

지금 시각: {time_str}
실시간 트위터 트렌드: {', '.join(trends)}

실제 트위터에서 수집한 트윗 샘플 (말투 참고용):
---
{samples}
---

위 실제 트윗들의 말투, 호흡, 문체를 학습해서 오꿈이 스타일로 트윗 10개 써줘.
트렌드 중 자연스럽게 녹일 수 있는 것만 써. 억지 언급 ㄴㄴ.

규칙:
- 트윗 텍스트만. 번호 따옴표 불릿 없이
- 빈 줄로 구분
- 10개 다 다른 주제/형식
- 짧고 세게. 한~두 문장
- 말 되게"""

    raw = generate_only(client, prompt)

    tweets = []
    for line in raw.split("\n"):
        line = line.strip()
        if not line:
            continue
        line = re.sub(r"^\d+[\.\)]\s*", "", line)
        if line:
            tweets.append(line)

    return tweets[:10]

# ── Discord 전송 ──────────────────────────────────────────────────────────────

def send_to_discord(tweets: list[str], trends: list[str]):
    kst = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)
    now_str = kst.strftime("%Y.%m.%d %H:%M KST")
    trend_str = " · ".join(trends[:6])

    lines = [
        f"🦆 **오꿈이 트윗 초안** `{now_str}`",
        f"📈 실시간 트렌드: `{trend_str}`",
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

    client = get_client()

    print("[1] 실시간 트렌드 수집 중...")
    try:
        trends = get_trends(client)
    except Exception as e:
        print(f"[트렌드 실패] {e} → 빈 목록으로 진행")
        trends = []

    print("[2] 실제 트윗 샘플 수집 중...")
    try:
        samples = get_tweet_samples(client, trends)
    except Exception as e:
        print(f"[샘플 수집 실패] {e} → 샘플 없이 진행")
        samples = ""

    print("[3] 오꿈이 트윗 생성 중...")
    tweets = generate_tweets(client, trends, samples)

    print(f"\n[결과 {len(tweets)}개]")
    for i, t in enumerate(tweets, 1):
        print(f"  {i}. {t}")

    send_to_discord(tweets, trends)
    print("\n완료!\n")

if __name__ == "__main__":
    main()
